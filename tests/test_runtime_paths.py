import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

import runtime_paths
from parker_label_app.category_store import CategoryStore
import parker_label_app.window as window_module


class PortablePathTests(unittest.TestCase):
    def test_source_and_frozen_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(runtime_paths, "_SOURCE_ROOT", root):
                self.assertEqual(runtime_paths.resource_root(), root)
                self.assertEqual(runtime_paths.config_directory(), root / "configs")
                self.assertEqual(runtime_paths.model_directory(), root / "pretrain")
                self.assertEqual(runtime_paths.model_manifest_path(), root / "model-bundle.json")
                self.assertEqual(
                    runtime_paths.application_icon_path(),
                    root / "parker_label_app" / "assets" / "app-icon.png",
                )
            with patch.object(runtime_paths.sys, "frozen", True, create=True), patch.object(
                runtime_paths.sys, "_MEIPASS", str(root / "internal"), create=True
            ), patch.object(runtime_paths.sys, "executable", str(root / "ParkerLabel.exe")):
                self.assertEqual(runtime_paths.resource_root(), root / "internal")
                self.assertEqual(runtime_paths.config_directory(), root / "configs")
                self.assertEqual(runtime_paths.model_directory(), root / "configs" / "pretrain")
                self.assertEqual(
                    runtime_paths.model_manifest_path(), root / "internal" / "model-bundle.json"
                )
                self.assertEqual(
                    runtime_paths.application_icon_path(),
                    root / "internal" / "parker_label_app" / "assets" / "app-icon.png",
                )
            executable = root / "ParkerLabel.app" / "Contents" / "MacOS" / "ParkerLabel"
            with patch.object(runtime_paths.sys, "frozen", True, create=True), patch.object(
                runtime_paths.sys, "executable", str(executable)
            ):
                self.assertEqual(runtime_paths.config_directory(), root / "configs")

    def test_startup_does_not_import_old_category_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "config" / "category-configs"
            original.mkdir(parents=True)
            (original / "Test.json").write_text("original", encoding="utf-8")
            logger = logging.getLogger("parker_label")
            with patch.object(runtime_paths, "_SOURCE_ROOT", root):
                runtime_paths.prepare_runtime()
                configs = root / "configs"
                self.assertTrue((configs / "categories").is_dir())
                self.assertFalse((configs / "categories" / "Test.json").exists())
                self.assertFalse((configs / "settings.ini").exists())
                self.assertFalse((configs / ".legacy-migration-complete").exists())
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()

    def test_window_loads_category_selected_beside_program(self):
        type(self)._app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            builtin = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
            (root / "config").mkdir()
            (root / "config" / "default-coco.json").write_bytes(builtin.read_bytes())
            configs = root / "configs"
            category_id = "11111111-1111-4111-8111-111111111111"
            categories = CategoryStore(builtin).load()[:1]
            CategoryStore(configs / "categories" / "Test.json").save(
                category_id, "2026-09-21T00:00:00+08:00", categories
            )
            settings = QSettings(str(configs / "settings.ini"), QSettings.IniFormat)
            settings.setValue("categories/default_config_uuid", category_id)
            settings.sync()
            with patch.object(window_module, "resource_root", return_value=root), patch.object(
                window_module, "config_directory", return_value=configs
            ), patch.object(
                window_module, "model_directory", return_value=root / "pretrain"
            ), patch.object(window_module, "SegmentationEngine", return_value=object()) as engine, patch.object(
                window_module,
                "portable_settings",
                return_value=settings,
            ):
                window = window_module.MainWindow()
            try:
                engine.assert_called_once_with(
                    root / "pretrain" / "encoder.onnx",
                    root / "pretrain" / "decoder.onnx",
                    target_size=1024,
                )
                self.assertEqual(window.active_category_config_id, category_id)
                self.assertEqual(window.category_manager.configuration(category_id).name, "Test")
            finally:
                window.close()
                self._app.processEvents()

    def test_each_start_clears_and_bounds_log_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logger = logging.getLogger("parker_label")
            with patch.object(runtime_paths, "_SOURCE_ROOT", root):
                runtime_paths.prepare_runtime()
                logger.info("previous launch")
                for handler in logger.handlers:
                    handler.flush()
                self.assertIn("previous launch", (root / "configs" / "app.log").read_text())
                for _ in range(1_100):
                    logger.info("x" * 1_000)
                backup = root / "configs" / "app.log.1"
                self.assertTrue(backup.exists())
                self.assertLessEqual(backup.stat().st_size, 1_000_000)
                self.assertLessEqual((root / "configs" / "app.log").stat().st_size, 1_000_000)
                runtime_paths.prepare_runtime()
                logger.info("current launch")
                for handler in logger.handlers:
                    handler.flush()
                content = (root / "configs" / "app.log").read_text()
                self.assertIn("current launch", content)
                self.assertNotIn("previous launch", content)
                self.assertFalse((root / "configs" / "app.log.1").exists())
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()


if __name__ == "__main__":
    unittest.main()

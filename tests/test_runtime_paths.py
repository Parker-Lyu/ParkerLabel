import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

import runtime_paths
from parker_label_app.category_store import CategoryConfigManager, CategoryStore
import parker_label_app.window as window_module


class PortablePathTests(unittest.TestCase):
    def test_source_and_frozen_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(runtime_paths, "_SOURCE_ROOT", root):
                self.assertEqual(runtime_paths.resource_root(), root)
                self.assertEqual(runtime_paths.config_directory(), root / "configs")
            with patch.object(runtime_paths.sys, "frozen", True, create=True), patch.object(
                runtime_paths.sys, "_MEIPASS", str(root / "internal"), create=True
            ), patch.object(runtime_paths.sys, "executable", str(root / "ParkerLabel.exe")):
                self.assertEqual(runtime_paths.resource_root(), root / "internal")
                self.assertEqual(runtime_paths.config_directory(), root / "configs")
            executable = root / "ParkerLabel.app" / "Contents" / "MacOS" / "ParkerLabel"
            with patch.object(runtime_paths.sys, "frozen", True, create=True), patch.object(
                runtime_paths.sys, "executable", str(executable)
            ):
                self.assertEqual(runtime_paths.config_directory(), root / "configs")

    def test_migrates_existing_categories_and_settings_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            builtin = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
            original = root / "config" / "category-configs"
            original.mkdir(parents=True)
            category_id = "11111111-1111-4111-8111-111111111111"
            categories = CategoryStore(builtin).load()[:1]
            CategoryStore(original / "道路场景.json").save(
                category_id, "2026-09-18T09:52:35+08:00", categories
            )
            (original / "settings.json").write_text(
                json.dumps({"default_config_uuid": category_id}), encoding="utf-8"
            )
            configs = root / "configs"
            with patch.object(runtime_paths, "_SOURCE_ROOT", root):
                runtime_paths._migrate_categories(configs)
                manager = CategoryConfigManager(
                    builtin,
                    user_directory=configs / "categories",
                    settings=QSettings(str(configs / "settings.ini"), QSettings.IniFormat),
                )
                self.assertEqual(manager.default_config_id(), category_id)
                self.assertEqual(manager.configuration(category_id).name, "道路场景")
                manager.set_default(CategoryConfigManager.BUILTIN_ID)
                manager.set_default(category_id)
                reloaded = CategoryConfigManager(
                    builtin,
                    user_directory=configs / "categories",
                    settings=QSettings(str(configs / "settings.ini"), QSettings.IniFormat),
                )
                self.assertEqual(reloaded.default_config_id(), category_id)
                (configs / "categories" / "道路场景.json").write_text("custom", encoding="utf-8")
                runtime_paths._migrate_categories(configs)
                self.assertEqual((configs / "categories" / "道路场景.json").read_text(), "custom")

            old_settings = QSettings(str(root / "old.ini"), QSettings.IniFormat)
            old_settings.setValue("interface/language", "ja_JP")
            old_settings.setValue("interface/quality_check_enabled", False)
            old_settings.setValue("shortcuts/save", "Ctrl+S")
            old_settings.setValue("AppleLocale", "en_US")
            old_settings.sync()
            with patch.object(runtime_paths, "_SOURCE_ROOT", root):
                runtime_paths._migrate_settings(configs, old_settings)
                self.assertEqual(runtime_paths.portable_settings().value("interface/language"), "ja_JP")
                self.assertFalse(runtime_paths.portable_settings().value("interface/quality_check_enabled"))
                self.assertEqual(runtime_paths.portable_settings().value("shortcuts/save"), "Ctrl+S")
                self.assertFalse(runtime_paths.portable_settings().contains("AppleLocale"))
                settings = runtime_paths.portable_settings()
                settings.setValue("interface/language", "en_US")
                settings.sync()
                runtime_paths._migrate_settings(configs, old_settings)
                self.assertEqual(runtime_paths.portable_settings().value("interface/language"), "en_US")

    def test_legacy_categories_are_migrated_only_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "config" / "category-configs"
            original.mkdir(parents=True)
            (original / "Test.json").write_text("original", encoding="utf-8")
            logger = logging.getLogger("parker_label")
            with patch.object(runtime_paths, "_SOURCE_ROOT", root), patch.object(
                runtime_paths, "_migrate_settings"
            ):
                runtime_paths.prepare_runtime()
                target = root / "configs" / "categories" / "Test.json"
                self.assertEqual(target.read_text(), "original")
                target.unlink()
                runtime_paths.prepare_runtime()
                self.assertFalse(target.exists())
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
            ), patch.object(window_module, "SegmentationEngine", return_value=object()), patch.object(
                window_module,
                "portable_settings",
                return_value=settings,
            ):
                window = window_module.MainWindow()
            try:
                self.assertEqual(window.active_category_config_id, category_id)
                self.assertEqual(window.category_manager.configuration(category_id).name, "Test")
            finally:
                window.close()
                self._app.processEvents()

    def test_each_start_clears_and_bounds_log_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logger = logging.getLogger("parker_label")
            with patch.object(runtime_paths, "_SOURCE_ROOT", root), patch.object(
                runtime_paths, "_migrate_settings"
            ):
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

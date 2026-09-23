import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

import parker_label_app.window as window_module


class OpenPreferencesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.directory.name) / "settings.ini"
        self.windows = []

    def tearDown(self):
        for window in self.windows:
            window.close()
        self.directory.cleanup()

    def create_window(self):
        settings = QSettings(str(self.settings_path), QSettings.IniFormat)
        with patch.object(window_module, "portable_settings", return_value=settings), patch.object(
            window_module, "SegmentationEngine", return_value=object()
        ):
            window = window_module.MainWindow()
        self.windows.append(window)
        return window

    def test_brush_size_defaults_to_three_and_survives_restart(self):
        first = self.create_window()
        self.assertEqual(first.brush_slider.value(), 3)
        first.brush_slider.setValue(12)
        self.assertEqual(self.create_window().brush_slider.value(), 12)

    def test_deleted_image_and_directory_use_existing_parent(self):
        first = self.create_window()
        image_directory = Path(self.directory.name) / "images"
        image_directory.mkdir()
        image = image_directory / "sample.png"
        cv2.imwrite(str(image), np.zeros((12, 12, 3), dtype=np.uint8))
        with patch.object(first, "ensure_embedding"):
            first.open_image(str(image))
        self.assertEqual(first.settings.value(first.LAST_IMAGE_SETTING_KEY), str(image.resolve()))

        image.unlink()
        second = self.create_window()
        with patch.object(window_module.QFileDialog, "getOpenFileName", return_value=("", "")) as picker:
            second.choose_image()
        self.assertEqual(picker.call_args.args[2], str(image_directory.resolve()))

        image_directory.rmdir()
        with patch.object(window_module.QFileDialog, "getOpenFileName", return_value=("", "")) as picker:
            second.choose_image()
        self.assertEqual(picker.call_args.args[2], str(Path(self.directory.name).resolve()))

    def test_failed_open_keeps_previous_image_directory(self):
        window = self.create_window()
        existing = Path(self.directory.name) / "previous.png"
        window.settings.setValue(window.LAST_IMAGE_SETTING_KEY, str(existing))
        with patch.object(window.repository, "open", side_effect=OSError("missing")), patch.object(
            window, "log_exception"
        ):
            window.open_image(str(Path(self.directory.name) / "other.png"))
        self.assertEqual(window.settings.value(window.LAST_IMAGE_SETTING_KEY), str(existing))


if __name__ == "__main__":
    unittest.main()

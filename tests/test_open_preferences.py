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

    def test_recent_images_show_five_valid_paths_and_open_on_click(self):
        window = self.create_window()
        images = []
        for index in range(7):
            image = Path(self.directory.name) / f"image-{index}.png"
            cv2.imwrite(str(image), np.zeros((12, 12, 3), dtype=np.uint8))
            images.append(image.resolve())
            with patch.object(window, "ensure_embedding"):
                window.open_image(str(image))

        images[-1].unlink()
        restarted = self.create_window()
        restarted.show()
        self.app.processEvents()
        self.assertEqual(restarted.canvas.recent_paths, list(reversed(images[1:6])))
        self.assertEqual(restarted.canvas.recent_label.text(), restarted.t("canvas.recent_images"))
        self.assertEqual(sum(button.isVisible() for button in restarted.canvas.recent_buttons), 5)
        with patch.object(restarted, "open_image") as open_image:
            restarted.canvas.recent_buttons[0].click()
        open_image.assert_called_once_with(str(images[5]))

        with patch.object(window, "ensure_embedding"):
            window.open_image(str(images[2]))
        newest = self.create_window()
        self.assertEqual(newest.canvas.recent_paths[0], images[2])
        self.assertEqual(len(set(newest.canvas.recent_paths)), 5)

    def test_existing_last_image_seeds_recent_history(self):
        previous = Path(self.directory.name) / "previous.png"
        current = Path(self.directory.name) / "current.png"
        for image in (previous, current):
            cv2.imwrite(str(image), np.zeros((12, 12, 3), dtype=np.uint8))
        window = self.create_window()
        window.settings.setValue(window.LAST_IMAGE_SETTING_KEY, str(previous))
        window.update_empty_canvas()
        self.assertEqual(window.canvas.recent_paths, [previous.resolve()])
        with patch.object(window, "ensure_embedding"):
            window.open_image(str(current))
        self.assertEqual(
            self.create_window().canvas.recent_paths,
            [current.resolve(), previous.resolve()],
        )


if __name__ == "__main__":
    unittest.main()

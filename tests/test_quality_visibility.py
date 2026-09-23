import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from parker_label_app.models import AnnotationDocument, Segment
import parker_label_app.window as window_module


class QualityVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        settings = QSettings(
            str(Path(self.directory.name) / "window.ini"), QSettings.IniFormat
        )
        with patch.object(window_module, "portable_settings", return_value=settings), patch.object(
            window_module, "SegmentationEngine", return_value=object()
        ):
            self.window = window_module.MainWindow()
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[2:12, 2:12] = 1
        mask[5:7, 5:7] = 0
        mask[15:17, 15:17] = 1
        self.window.document = AnnotationDocument(
            Path(self.directory.name) / "image.png",
            np.zeros((20, 20, 3), dtype=np.uint8),
            (20, 20),
            segments=[Segment(1, "object", 255, mask=mask)],
        )
        self.window.current_index = 0
        self.window.canvas_size = (20, 20)
        self.window.quality_check_enabled = True
        self.window.refresh_table()
        self.window.update_mask_quality()

    def tearDown(self):
        self.window.close()
        self.directory.cleanup()

    def test_boxes_follow_row_and_header_visibility(self):
        self.assertEqual(self.window.mask_quality.mask_region_count, 2)
        self.assertEqual(self.window.mask_quality.hole_count, 1)
        with patch.object(self.window, "draw_quality_boxes") as draw_boxes:
            self.window.refresh_canvas()
            draw_boxes.assert_called_once()

            draw_boxes.reset_mock()
            self.window.set_segment_visibility(0, False)
            draw_boxes.assert_not_called()

            self.window.set_all_segments_visible(True)
            draw_boxes.assert_called_once()

            draw_boxes.reset_mock()
            self.window.set_all_segments_visible(False)
            draw_boxes.assert_not_called()


if __name__ == "__main__":
    unittest.main()

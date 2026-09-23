import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5.QtCore import QPoint, QSettings
from PyQt5.QtWidgets import QApplication

from parker_label_app.models import AnnotationDocument
import parker_label_app.window as window_module


class CanvasPanTests(unittest.TestCase):
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
        self.window.document = AnnotationDocument(
            Path(self.directory.name) / "image.png",
            np.zeros((200, 300, 3), dtype=np.uint8),
            (200, 300),
        )
        self.window.quality_check_enabled = False
        self.window.show()
        self.app.processEvents()
        viewport = self.window.scroll_area.viewport()
        self.window.base_canvas_size = (viewport.width() + 200, viewport.height() + 200)
        self.window.apply_canvas_size()
        self.window.refresh_canvas()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.directory.cleanup()

    def test_middle_button_pan_moves_image_edges_into_viewport(self):
        viewport = self.window.scroll_area.viewport()
        scrollbar = self.window.scroll_area.horizontalScrollBar()
        margin = self.window.CANVAS_PAN_MARGIN
        scrollbar.setValue(margin)
        self.assertEqual(self.window.canvas.mapTo(viewport, QPoint(0, 0)).x(), 0)

        self.window.panning = True
        self.window.pan_origin = QPoint(0, 0)
        self.window.canvas_mouse_move(SimpleNamespace(globalPos=lambda: QPoint(margin, 0)))
        self.assertEqual(scrollbar.value(), 0)
        self.assertEqual(self.window.canvas.mapTo(viewport, QPoint(0, 0)).x(), margin)

        scrollbar.setValue(scrollbar.maximum())
        right = self.window.canvas.mapTo(
            viewport, QPoint(self.window.canvas.width(), 0)
        ).x()
        self.assertEqual(viewport.width() - right, margin)

    def test_wheel_zoom_keeps_image_anchor_in_place(self):
        viewport = self.window.scroll_area.viewport()
        scrollbar = self.window.scroll_area.horizontalScrollBar()
        scrollbar.setValue(scrollbar.maximum() // 2)
        vertical = self.window.scroll_area.verticalScrollBar()
        vertical.setValue(vertical.maximum() // 2)
        anchor = QPoint(100, 100)
        before = self.window.canvas.mapTo(viewport, anchor)
        event = SimpleNamespace(
            pos=lambda: anchor,
            angleDelta=lambda: QPoint(0, 120),
            accept=lambda: None,
        )
        self.window.canvas_wheel(event)
        scaled_anchor = QPoint(
            round(anchor.x() * self.window.zoom_step),
            round(anchor.y() * self.window.zoom_step),
        )
        after = self.window.canvas.mapTo(viewport, scaled_anchor)
        self.assertLessEqual(abs(after.x() - before.x()), 1)
        self.assertLessEqual(abs(after.y() - before.y()), 1)

    def test_fitting_image_has_no_extra_horizontal_scroll(self):
        viewport = self.window.scroll_area.viewport()
        self.window.base_canvas_size = (viewport.width() // 2, viewport.height() // 2)
        self.window.apply_canvas_size()
        self.app.processEvents()
        self.assertEqual(self.window.canvas.pos().x(), 0)
        self.assertEqual(self.window.scroll_area.horizontalScrollBar().maximum(), 0)

    def test_zoom_into_overflow_preserves_cursor_anchor(self):
        viewport = self.window.scroll_area.viewport()
        self.window.base_canvas_size = (viewport.width() - 20, viewport.height() + 200)
        self.window.apply_canvas_size()
        self.app.processEvents()
        anchor = QPoint(self.window.canvas.width() // 2, 100)
        before = self.window.canvas.mapTo(viewport, anchor)
        event = SimpleNamespace(
            pos=lambda: anchor,
            angleDelta=lambda: QPoint(0, 120),
            accept=lambda: None,
        )
        self.window.canvas_wheel(event)
        scaled_anchor = QPoint(round(anchor.x() * self.window.zoom_step), 100)
        after = self.window.canvas.mapTo(viewport, scaled_anchor)
        self.assertEqual(self.window.canvas.pos().x(), self.window.CANVAS_PAN_MARGIN)
        self.assertLessEqual(abs(after.x() - before.x()), 1)


if __name__ == "__main__":
    unittest.main()

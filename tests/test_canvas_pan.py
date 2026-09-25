import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5.QtCore import QPoint, QPointF, QSettings, Qt
from PyQt5.QtGui import QNativeGestureEvent
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
        horizontal = self.window.scroll_area.horizontalScrollBar()
        vertical = self.window.scroll_area.verticalScrollBar()
        horizontal_margin = viewport.width() // 2
        vertical_margin = viewport.height() // 2
        horizontal.setValue(horizontal_margin)
        vertical.setValue(vertical_margin)
        self.assertEqual(self.window.canvas.mapTo(viewport, QPoint(0, 0)), QPoint(0, 0))

        self.window.panning = True
        self.window.pan_origin = QPoint(0, 0)
        self.window.canvas_mouse_move(SimpleNamespace(globalPos=lambda: QPoint(horizontal_margin, vertical_margin)))
        self.assertEqual(horizontal.value(), 0)
        self.assertEqual(vertical.value(), 0)
        self.assertEqual(
            self.window.canvas.mapTo(viewport, QPoint(0, 0)), QPoint(horizontal_margin, vertical_margin)
        )

        horizontal.setValue(horizontal.maximum())
        vertical.setValue(vertical.maximum())
        bottom_right = self.window.canvas.mapTo(
            viewport, QPoint(self.window.canvas.width(), self.window.canvas.height())
        )
        self.assertEqual(viewport.width() - bottom_right.x(), horizontal_margin)
        self.assertEqual(viewport.height() - bottom_right.y(), vertical_margin)

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
            source=lambda: Qt.MouseEventNotSynthesized,
            modifiers=lambda: Qt.NoModifier,
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

    def test_fitting_image_can_pan_with_half_viewport_margin(self):
        viewport = self.window.scroll_area.viewport()
        self.window.base_canvas_size = (viewport.width() // 2, viewport.height() // 2)
        self.window.apply_canvas_size()
        self.app.processEvents()
        self.window.center_canvas_view()
        horizontal = self.window.scroll_area.horizontalScrollBar()
        vertical = self.window.scroll_area.verticalScrollBar()
        self.assertGreater(horizontal.maximum(), 0)
        self.assertGreater(vertical.maximum(), 0)
        centered = self.window.canvas.mapTo(viewport, QPoint(0, 0))
        self.assertLessEqual(
            abs(centered.x() - (viewport.width() - self.window.canvas.width()) // 2), 1
        )
        self.assertLessEqual(
            abs(centered.y() - (viewport.height() - self.window.canvas.height()) // 2), 1
        )

        horizontal.setValue(0)
        vertical.setValue(0)
        self.assertEqual(
            self.window.canvas.mapTo(viewport, QPoint(0, 0)),
            QPoint(viewport.width() // 2, viewport.height() // 2),
        )
        horizontal.setValue(horizontal.maximum())
        vertical.setValue(vertical.maximum())
        right_bottom = self.window.canvas.mapTo(
            viewport, QPoint(self.window.canvas.width(), self.window.canvas.height())
        )
        self.assertEqual(viewport.width() - right_bottom.x(), viewport.width() // 2)
        self.assertEqual(viewport.height() - right_bottom.y(), viewport.height() // 2)

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
            source=lambda: Qt.MouseEventNotSynthesized,
            modifiers=lambda: Qt.NoModifier,
            accept=lambda: None,
        )
        self.window.canvas_wheel(event)
        scaled_anchor = QPoint(round(anchor.x() * self.window.zoom_step), 100)
        after = self.window.canvas.mapTo(viewport, scaled_anchor)
        self.assertEqual(self.window.canvas.pos().x(), viewport.width() // 2)
        self.assertLessEqual(abs(after.x() - before.x()), 1)

    def test_vertical_zoom_into_overflow_preserves_cursor_anchor(self):
        viewport = self.window.scroll_area.viewport()
        self.window.base_canvas_size = (viewport.width() + 200, viewport.height() - 20)
        self.window.apply_canvas_size()
        self.app.processEvents()
        anchor = QPoint(100, self.window.canvas.height() // 2)
        before = self.window.canvas.mapTo(viewport, anchor)
        event = SimpleNamespace(
            pos=lambda: anchor,
            angleDelta=lambda: QPoint(0, 120),
            source=lambda: Qt.MouseEventNotSynthesized,
            modifiers=lambda: Qt.NoModifier,
            accept=lambda: None,
        )
        self.window.canvas_wheel(event)
        scaled_anchor = QPoint(100, round(anchor.y() * self.window.zoom_step))
        after = self.window.canvas.mapTo(viewport, scaled_anchor)
        self.assertEqual(self.window.canvas.pos().y(), viewport.height() // 2)
        self.assertLessEqual(abs(after.y() - before.y()), 1)

    def test_touchpad_scroll_pans_both_axes_without_zooming(self):
        horizontal = self.window.scroll_area.horizontalScrollBar()
        vertical = self.window.scroll_area.verticalScrollBar()
        horizontal.setValue(horizontal.maximum() // 2)
        vertical.setValue(vertical.maximum() // 2)
        before = (horizontal.value(), vertical.value())
        event = SimpleNamespace(
            source=lambda: Qt.MouseEventSynthesizedBySystem,
            modifiers=lambda: Qt.NoModifier,
            pixelDelta=lambda: QPoint(17, -23),
            angleDelta=lambda: QPoint(0, 0),
            accept=lambda: None,
        )
        self.window.canvas_wheel(event)
        self.assertEqual((horizontal.value(), vertical.value()), (before[0] - 17, before[1] + 23))
        self.assertEqual(self.window.zoom_factor, 1.0)

    def test_native_pinch_zooms_and_keeps_anchor(self):
        viewport = self.window.scroll_area.viewport()
        anchor = QPoint(100, 100)
        before = self.window.canvas.mapTo(viewport, anchor)
        event = SimpleNamespace(
            gestureType=lambda: Qt.ZoomNativeGesture,
            value=lambda: 0.15,
            pos=lambda: anchor,
            accept=lambda: None,
        )
        with patch.object(window_module.sys, "platform", "darwin"):
            self.assertTrue(self.window.canvas_native_gesture(event))
        self.assertAlmostEqual(self.window.zoom_factor, 1.15)
        scaled_anchor = QPoint(round(anchor.x() * 1.15), round(anchor.y() * 1.15))
        after = self.window.canvas.mapTo(viewport, scaled_anchor)
        self.assertLessEqual(abs(after.x() - before.x()), 1)
        self.assertLessEqual(abs(after.y() - before.y()), 1)

    def test_windows_native_pinch_uses_relative_distance(self):
        anchor = QPoint(100, 100)

        def gesture(value):
            return SimpleNamespace(
                gestureType=lambda: Qt.ZoomNativeGesture,
                value=lambda: value,
                pos=lambda: anchor,
                accept=lambda: None,
            )

        with patch.object(window_module.sys, "platform", "win32"):
            self.window.canvas_native_gesture(gesture(100))
            self.assertEqual(self.window.zoom_factor, 1.0)
            self.window.canvas_native_gesture(gesture(115))
        self.assertAlmostEqual(self.window.zoom_factor, 1.15)

    def test_canvas_receives_native_gesture_event(self):
        point = QPointF(100, 100)
        event = QNativeGestureEvent(
            Qt.ZoomNativeGesture, point, point, point, 0.15, 1, 0
        )
        with patch.object(window_module.sys, "platform", "darwin"):
            QApplication.sendEvent(self.window.canvas, event)
        self.assertTrue(event.isAccepted())
        self.assertAlmostEqual(self.window.zoom_factor, 1.15)

    def test_ctrl_wheel_zooms_for_windows_touchpad_fallback(self):
        event = SimpleNamespace(
            source=lambda: Qt.MouseEventSynthesizedBySystem,
            modifiers=lambda: Qt.ControlModifier,
            angleDelta=lambda: QPoint(0, 120),
            pos=lambda: QPoint(100, 100),
            accept=lambda: None,
        )
        self.window.canvas_wheel(event)
        self.assertAlmostEqual(self.window.zoom_factor, 1.15)

    def test_view_buttons_zoom_and_reset(self):
        self.window.update_view_controls()
        self.assertTrue(self.window.view_controls.isVisible())
        self.assertEqual(self.window.view_controls.pos(), QPoint(8, 8))
        self.window.zoom_in_button.click()
        self.assertGreater(self.window.zoom_factor, 1)
        self.window.zoom_out_button.click()
        self.assertAlmostEqual(self.window.zoom_factor, 1)
        self.window.zoom_in_button.click()
        self.window.reset_view_button.click()
        self.assertEqual(self.window.zoom_factor, 1)
        horizontal = self.window.scroll_area.horizontalScrollBar()
        vertical = self.window.scroll_area.verticalScrollBar()
        self.assertEqual(horizontal.value(), horizontal.maximum() // 2)
        self.assertEqual(vertical.value(), vertical.maximum() // 2)


if __name__ == "__main__":
    unittest.main()

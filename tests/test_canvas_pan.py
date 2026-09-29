import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5.QtCore import QPoint, QPointF, QSettings, Qt
from PyQt5.QtGui import QImage, QNativeGestureEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QFrame, QToolButton

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

    def test_prompt_point_visibility_button_and_shortcut(self):
        self.window.prompt_points = [(50, 60)]
        self.window.prompt_labels = [1]
        self.window.refresh_canvas()
        point = QPoint(
            int(50 * self.window.canvas_size[0] / 300),
            int(60 * self.window.canvas_size[1] / 200),
        )
        shown = self.window.canvas.pixmap().toImage().pixelColor(point)
        self.assertGreater(shown.green(), shown.red())
        layout = self.window.view_controls.layout()
        self.assertEqual(layout.itemAt(7).widget().frameShape(), QFrame.VLine)
        self.assertIs(layout.itemAt(8).widget(), self.window.prompt_points_button)
        self.assertIs(layout.itemAt(9).widget(), self.window.quality_button)
        self.assertIn("S", self.window.prompt_points_button.toolTip())

        self.window.prompt_points_button.click()
        hidden = self.window.canvas.pixmap().toImage().pixelColor(point)
        self.assertEqual(hidden.red(), 0)
        self.assertEqual(hidden.green(), 0)
        self.assertFalse(self.window.prompt_points_button.isChecked())
        self.assertEqual(len(self.window.prompt_points), 1)
        self.assertFalse(self.window.settings.value(self.window.PROMPT_POINTS_SETTING_KEY, type=bool))

        self.window.canvas.setFocus()
        QTest.keyClick(self.window.canvas, Qt.Key_S)
        self.assertTrue(self.window.prompt_points_button.isChecked())
        self.assertGreater(
            self.window.canvas.pixmap().toImage().pixelColor(point).green(), 0
        )

    def test_quality_button_and_shortcut(self):
        self.assertTrue(self.window.quality_button.isChecked())
        self.assertIn("C", self.window.quality_button.toolTip())
        self.window.quality_button.click()
        self.assertFalse(self.window.quality_check_enabled)
        self.assertFalse(self.window.quality_button.isChecked())
        self.assertFalse(self.window.settings.value(self.window.QUALITY_SETTING_KEY, type=bool))
        self.assertIn(self.window.t("canvas.enable_quality"), self.window.quality_button.toolTip())
        self.window.canvas.setFocus()
        QTest.keyClick(self.window.canvas, Qt.Key_C)
        self.assertTrue(self.window.quality_check_enabled)
        self.assertTrue(self.window.quality_button.isChecked())

    def test_target_editing_buttons_are_on_canvas(self):
        layout = self.window.view_controls.layout()
        self.assertEqual(layout.itemAt(10).widget().frameShape(), QFrame.VLine)
        for index, button, key in (
            (11, self.window.undo_button, "main.undo"),
            (12, self.window.redo_button, "main.redo"),
            (13, self.window.add_button, "main.add_target"),
            (14, self.window.discard_button, "main.discard_changes"),
            (15, self.window.commit_button, "main.commit_target"),
        ):
            self.assertIs(layout.itemAt(index).widget(), button)
            self.assertIsInstance(button, QToolButton)
            self.assertEqual(button.parentWidget(), self.window.view_controls)
            self.assertEqual(button.text(), "")
            self.assertEqual(button.accessibleName(), self.window.t(key))
            self.assertIn(self.window.t(key), button.toolTip())
            self.assertFalse(button.icon().isNull())
        self.assertIn(self.window.t("tooltip.discard_changes"), self.window.discard_button.toolTip())
        self.assertIn(self.window.t("tooltip.commit_target"), self.window.commit_button.toolTip())
        self.assertFalse(hasattr(self.window, "edit_group"))

        self.window.update_editing_state()
        self.assertTrue(self.window.add_button.isEnabled())
        with patch.object(self.window, "show_warning") as warning:
            self.window.add_button.click()
        warning.assert_not_called()
        self.assertEqual(len(self.window.document.segments), 1)
        self.assertFalse(self.window.undo_button.isEnabled())
        self.assertFalse(self.window.redo_button.isEnabled())
        self.window.document.dirty = False

    def test_view_mode_buttons_are_grouped_between_zoom_and_points(self):
        layout = self.window.view_controls.layout()
        self.assertEqual(layout.itemAt(3).widget().frameShape(), QFrame.VLine)
        for index, button, value, shortcut in (
            (4, self.window.image_view_button, "image", "1"),
            (5, self.window.mask_view_button, "mask", "2"),
            (6, self.window.overlay_view_button, "overlay", "3"),
        ):
            self.assertIs(layout.itemAt(index).widget(), button)
            self.assertIs(button.parentWidget(), self.window.view_controls)
            self.assertEqual(button.text(), "")
            self.assertEqual(button.accessibleName(), self.window.t(f"main.view.{value}"))
            self.assertIn(button.accessibleName(), button.toolTip())
            self.assertIn(shortcut, button.toolTip())
        self.assertFalse(hasattr(self.window, "view_group_box"))
        self.assertTrue(self.window.overlay_view_button.isChecked())

        self.assertEqual(
            [layout.itemAt(index).widget().frameShape() for index in (3, 7, 10)],
            [QFrame.VLine] * 3,
        )

        self.window.mask_view_button.click()
        self.assertEqual(self.window.view_mode, "mask")
        self.assertTrue(self.window.mask_view_button.isChecked())
        self.assertFalse(self.window.overlay_view_button.isChecked())

        self.window.canvas.setFocus()
        QTest.keyClick(self.window.canvas, Qt.Key_1)
        self.assertEqual(self.window.view_mode, "image")
        self.assertTrue(self.window.image_view_button.isChecked())
        self.assertFalse(self.window.mask_view_button.isChecked())

    def test_canvas_icon_assets_load(self):
        directory = window_module.resource_root() / "parker_label_app" / "assets" / "canvas-icons"
        for kind, name in window_module.CANVAS_ICON_NAMES.items():
            icon = window_module.view_control_icon(kind)
            self.assertFalse(icon.isNull(), kind)
            self.assertTrue({24, 48, 72}.issubset({size.width() for size in icon.availableSizes()}))
            image = icon.pixmap(24, 24).toImage()
            self.assertGreater(
                sum(image.pixelColor(x, y).alpha() > 0 for x in range(24) for y in range(24)),
                0,
                kind,
            )
            for scale in (1, 2, 3):
                suffix = f"@{scale}x" if scale > 1 else ""
                asset = QImage(str(directory / f"{name}{suffix}.png"))
                self.assertFalse(asset.isNull(), f"{kind} {scale}x")
                self.assertEqual(asset.width(), 24 * scale)
                self.assertEqual(asset.height(), 24 * scale)

    def test_empty_canvas_shows_drag_guidance_and_current_shortcut(self):
        self.window.document = None
        self.window.reset_document_view()
        self.app.processEvents()
        self.assertEqual(self.window.canvas.size(), self.window.scroll_area.viewport().size())
        self.assertEqual(
            self.window.canvas.empty_state,
            (
                self.window.t("canvas.open_image"),
                self.window.t("canvas.drop_image"),
                self.window.t("canvas.open_shortcut", shortcut=self.window.shortcut_manager.shortcut_text("open_image")),
            ),
        )
        self.assertFalse(self.window.view_controls.isVisible())
        self.window.shortcut_manager.config["open_image"] = "Ctrl+P"
        self.window.shortcuts_changed()
        self.assertIn(self.window.shortcut_manager.shortcut_text("open_image"), self.window.canvas.empty_state[2])
        self.window.shortcut_manager.config["open_image"] = ""
        self.window.shortcuts_changed()
        self.assertEqual(self.window.canvas.empty_state[2], "")

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

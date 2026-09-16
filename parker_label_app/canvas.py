from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QLabel


class AnnotationCanvas(QLabel):
    def __init__(self, parent=None):
        """Create an image canvas that delegates interaction to its controller."""
        super().__init__(parent)
        self.controller = parent
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.brush_cursor_position = None

    def mousePressEvent(self, event):
        """Forward mouse press events to the annotation controller."""
        self.update_brush_cursor(event.pos())
        self.controller.canvas_mouse_press(event)

    def mouseMoveEvent(self, event):
        """Forward mouse move events to the annotation controller."""
        self.update_brush_cursor(event.pos())
        self.controller.canvas_mouse_move(event)

    def mouseReleaseEvent(self, event):
        """Forward mouse release events to the annotation controller."""
        self.update_brush_cursor(event.pos())
        self.controller.canvas_mouse_release(event)

    def wheelEvent(self, event):
        """Forward wheel events to the annotation controller."""
        self.clear_brush_cursor()
        self.controller.canvas_wheel(event)

    def leaveEvent(self, event):
        """Hide the brush outline when the pointer leaves the canvas."""
        self.clear_brush_cursor()
        super().leaveEvent(event)

    def update_brush_cursor(self, position):
        """Move the brush outline to the current canvas position."""
        if self.controller.mode != "brush" or self.controller.document is None:
            self.clear_brush_cursor()
            return
        self.brush_cursor_position = position
        self.update()

    def clear_brush_cursor(self):
        """Clear the brush outline from the canvas."""
        if self.brush_cursor_position is None:
            return
        self.brush_cursor_position = None
        self.update()

    def paintEvent(self, event):
        """Render the image and the active brush outline."""
        super().paintEvent(event)
        if (
            self.brush_cursor_position is None
            or self.controller.mode != "brush"
            or self.controller.document is None
        ):
            return
        image_height, image_width = self.controller.document.image_rgb.shape[:2]
        radius = self.controller.brush_slider.value()
        radius_x = radius * self.width() / image_width
        radius_y = radius * self.height() / image_height
        position = self.brush_cursor_position
        ellipse = QRectF(
            position.x() - radius_x,
            position.y() - radius_y,
            radius_x * 2,
            radius_y * 2,
        )
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.NoBrush)
        outer_pen = QPen(Qt.white, 3)
        outer_pen.setCosmetic(True)
        painter.setPen(outer_pen)
        painter.drawEllipse(ellipse)
        inner_pen = QPen(QColor(30, 30, 30), 2)
        inner_pen.setCosmetic(True)
        painter.setPen(inner_pen)
        painter.drawEllipse(ellipse)
        painter.end()

    def dragEnterEvent(self, event):
        """Accept drag events that contain local files."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Forward the first dropped file to the annotation controller."""
        urls = event.mimeData().urls()
        if urls:
            self.controller.open_image(urls[0].toLocalFile())
            event.acceptProposedAction()

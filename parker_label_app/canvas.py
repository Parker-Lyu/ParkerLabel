from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class AnnotationCanvas(QLabel):
    def __init__(self, parent=None):
        """Create an image canvas that delegates interaction to its controller."""
        super().__init__(parent)
        self.controller = parent
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.brush_cursor_position = None
        self.empty_state = ("", "", "")
        self.recent_paths = []
        self.recent_panel = QFrame(self)
        self.recent_panel.setFixedWidth(420)
        recent_layout = QVBoxLayout(self.recent_panel)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(4)
        self.recent_label = QLabel(self.recent_panel)
        self.recent_label.setStyleSheet("color: #34495e; font-weight: bold;")
        recent_layout.addWidget(self.recent_label)
        self.recent_buttons = []
        for index in range(5):
            button = QPushButton(self.recent_panel)
            button.setFixedHeight(30)
            button.setStyleSheet(
                "QPushButton { text-align: left; padding: 3px 10px; color: #34495e; "
                "background: white; border: 1px solid #cbd6e2; border-radius: 5px; }"
                "QPushButton:hover { background: #e7eef7; }"
            )
            button.clicked.connect(lambda _checked=False, row=index: self.open_recent_image(row))
            recent_layout.addWidget(button)
            self.recent_buttons.append(button)
        self.recent_panel.hide()

    def set_empty_state(self, title, hint, shortcut):
        self.empty_state = (title, hint, shortcut)
        self.update()

    def set_recent_images(self, title, paths):
        self.recent_paths = list(paths[:5])
        self.recent_label.setText(title)
        for index, button in enumerate(self.recent_buttons):
            visible = index < len(self.recent_paths)
            button.setVisible(visible)
            if visible:
                path = self.recent_paths[index]
                button.setText(button.fontMetrics().elidedText(path.name, Qt.ElideMiddle, 390))
                button.setToolTip(str(path))
        self.recent_panel.setVisible(bool(self.recent_paths))
        self.recent_panel.adjustSize()
        self.position_recent_panel()

    def open_recent_image(self, index):
        if index < len(self.recent_paths):
            self.controller.open_image(str(self.recent_paths[index]))

    def position_recent_panel(self):
        self.recent_panel.move(
            max(0, (self.width() - self.recent_panel.width()) // 2),
            min(self.height() // 2 + 90, max(8, self.height() - self.recent_panel.height() - 8)),
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_recent_panel()

    def event(self, event):
        if event.type() == QEvent.NativeGesture:
            if self.controller.canvas_native_gesture(event):
                return True
        return super().event(event)

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
        if self.controller.document is None:
            self.paint_empty_state()
            return
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

    def paint_empty_state(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))
        center = QPointF(self.width() / 2, self.height() / 2)
        icon = QRectF(center.x() - 38, center.y() - 105, 76, 66)
        painter.setBrush(QColor("#eef4fb"))
        painter.setPen(QPen(QColor("#8ba2ba"), 1.5, Qt.DashLine))
        painter.drawRoundedRect(icon, 10, 10)
        painter.setPen(QPen(QColor("#52708f"), 2.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(center.x(), icon.top() + 15), QPointF(center.x(), icon.top() + 40))
        painter.drawLine(QPointF(center.x() - 8, icon.top() + 32), QPointF(center.x(), icon.top() + 40))
        painter.drawLine(QPointF(center.x() + 8, icon.top() + 32), QPointF(center.x(), icon.top() + 40))
        painter.drawLine(QPointF(center.x() - 15, icon.bottom() - 14), QPointF(center.x() + 15, icon.bottom() - 14))
        title, hint, shortcut = self.empty_state
        font = QFont(self.font())
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#34495e"))
        painter.drawText(QRectF(20, center.y() - 20, self.width() - 40, 32), Qt.AlignCenter, title)
        font.setPointSize(11)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#65788d"))
        painter.drawText(QRectF(20, center.y() + 18, self.width() - 40, 28), Qt.AlignCenter, hint)
        painter.drawText(QRectF(20, center.y() + 48, self.width() - 40, 28), Qt.AlignCenter, shortcut)
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

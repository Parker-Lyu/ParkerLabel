from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel


class AnnotationCanvas(QLabel):
    def __init__(self, parent=None):
        """Create an image canvas that delegates interaction to its controller."""
        super().__init__(parent)
        self.controller = parent
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        """Forward mouse press events to the annotation controller."""
        self.controller.canvas_mouse_press(event)

    def mouseMoveEvent(self, event):
        """Forward mouse move events to the annotation controller."""
        self.controller.canvas_mouse_move(event)

    def mouseReleaseEvent(self, event):
        """Forward mouse release events to the annotation controller."""
        self.controller.canvas_mouse_release(event)

    def wheelEvent(self, event):
        """Forward wheel events to the annotation controller."""
        self.controller.canvas_wheel(event)

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

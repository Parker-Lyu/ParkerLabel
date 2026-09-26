from pathlib import Path

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication


def render_icons(directory):
    for source in sorted(directory.glob("*.svg")):
        svg = source.read_bytes().replace(b"currentColor", b"#344054")
        renderer = QSvgRenderer(QByteArray(svg))
        if not renderer.isValid():
            raise ValueError(f"invalid SVG: {source}")
        image = QImage(96, 96, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        if not image.save(str(source.with_suffix(".png"))):
            raise OSError(f"could not render {source}")


if __name__ == "__main__":
    QApplication([])
    render_icons(Path(__file__).resolve().parents[1] / "parker_label_app" / "assets" / "canvas-icons")

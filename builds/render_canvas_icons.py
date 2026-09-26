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
        for scale in (1, 2, 3):
            size = 24 * scale
            image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.transparent)
            painter = QPainter(image)
            renderer.render(painter)
            painter.end()
            suffix = f"@{scale}x" if scale > 1 else ""
            output = source.with_name(f"{source.stem}{suffix}.png")
            if not image.save(str(output)):
                raise OSError(f"could not render {source}")


if __name__ == "__main__":
    QApplication([])
    render_icons(Path(__file__).resolve().parents[1] / "parker_label_app" / "assets" / "canvas-icons")

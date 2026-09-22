#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


QT_MODULES = (
    "Qt5Bluetooth.dll", "Qt5Designer.dll", "Qt5Help.dll", "Qt5Location.dll",
    "Qt5Multimedia.dll", "Qt5MultimediaWidgets.dll", "Qt5NetworkAuth.dll",
    "Qt5Nfc.dll", "Qt5OpenGL.dll", "Qt5Positioning.dll", "Qt5Qml.dll",
    "Qt5QmlModels.dll", "Qt5Quick.dll", "Qt5QuickWidgets.dll",
    "Qt5RemoteObjects.dll", "Qt5Sensors.dll", "Qt5SerialPort.dll", "Qt5Sql.dll",
    "Qt5Svg.dll", "Qt5Test.dll", "Qt5TextToSpeech.dll", "Qt5WebChannel.dll",
    "Qt5WebSockets.dll", "Qt5Xml.dll", "Qt5XmlPatterns.dll",
)

QT_PLUGIN_PATHS = (
    "bearer", "generic", "iconengines", "imageformats", "platforminputcontexts",
    "platformthemes", "printsupport", "sqldrivers", "tls",
    "platforms/qminimal.dll", "platforms/qoffscreen.dll", "platforms/qwebgl.dll",
)


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    qt_root = args.app / "_internal" / "PyQt5" / "Qt5"
    for name in QT_MODULES:
        remove(qt_root / "bin" / name)
    for relative_path in QT_PLUGIN_PATHS:
        remove(qt_root / "plugins" / relative_path)
    remove(args.app / "_internal" / "cv2" / "opencv_videoio_ffmpeg500_64.dll")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


QT_FRAMEWORKS = (
    "QtNetwork.framework",
    "QtQml.framework",
    "QtQmlModels.framework",
    "QtQuick.framework",
    "QtSvg.framework",
    "QtWebSockets.framework",
)

QT_PLUGIN_PATHS = (
    "generic",
    "iconengines",
    "imageformats",
    "platforms/libqminimal.dylib",
    "platforms/libqoffscreen.dylib",
    "platforms/libqwebgl.dylib",
    "platformthemes",
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
    qt_root = args.app / "Contents" / "Frameworks" / "PyQt5" / "Qt5"
    for name in QT_FRAMEWORKS:
        remove(qt_root / "lib" / name)
    for relative_path in QT_PLUGIN_PATHS:
        remove(qt_root / "plugins" / relative_path)
    for path in args.app.rglob("*"):
        if path.is_symlink() and not path.exists():
            path.unlink()


if __name__ == "__main__":
    main()

import os
import sys
from pathlib import Path


project_root = Path(SPECPATH).parent
generated_dir = project_root / "builds" / ".generated"
app_version = os.environ.get("PARKER_LABEL_VERSION", "dev")
app_icon_png = project_root / "parker_label_app" / "assets" / "app-icon.png"
app_icon_ico = project_root / "parker_label_app" / "assets" / "app-icon.ico"

datas = [
    (str(project_root / "config" / "default-coco.json"), "config"),
    (str(project_root / "LICENSE"), "."),
    (str(project_root / "model-bundle.json"), "."),
    (str(generated_dir / "pretrain" / "encoder.onnx"), "pretrain"),
    (str(generated_dir / "pretrain" / "decoder.onnx"), "pretrain"),
    (str(project_root / "parker_label_app" / "assets"), "parker_label_app/assets"),
    (str(project_root / "parker_label_app" / "locales"), "parker_label_app/locales"),
    (str(generated_dir / "third_party_licenses"), "third_party_licenses"),
    (str(generated_dir / "build-info.json"), "."),
]

excluded_modules = [
    "PIL",
    "PyQt5.QtBluetooth",
    "PyQt5.QtDesigner",
    "PyQt5.QtHelp",
    "PyQt5.QtLocation",
    "PyQt5.QtMultimedia",
    "PyQt5.QtMultimediaWidgets",
    "PyQt5.QtNetworkAuth",
    "PyQt5.QtNfc",
    "PyQt5.QtOpenGL",
    "PyQt5.QtPositioning",
    "PyQt5.QtQml",
    "PyQt5.QtQuick",
    "PyQt5.QtQuickWidgets",
    "PyQt5.QtRemoteObjects",
    "PyQt5.QtSensors",
    "PyQt5.QtSerialPort",
    "PyQt5.QtSql",
    "PyQt5.QtSvg",
    "PyQt5.QtTest",
    "PyQt5.QtTextToSpeech",
    "PyQt5.QtWebChannel",
    "PyQt5.QtWebEngine",
    "PyQt5.QtWebEngineCore",
    "PyQt5.QtWebEngineWidgets",
    "PyQt5.QtWebSockets",
    "PyQt5.QtXml",
    "PyQt5.QtXmlPatterns",
    "matplotlib",
    "mobile_sam",
    "onnx",
    "pandas",
    "scipy",
    "sympy",
    "test",
    "tests",
    "tkinter",
    "torch",
    "torchvision",
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="ParkerLabel",
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=False,
        console=False,
        target_arch="arm64",
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=True,
        upx=False,
        name="ParkerLabel",
    )
    app = BUNDLE(
        coll,
        name="ParkerLabel.app",
        icon=str(app_icon_png),
        bundle_identifier="com.parkerlyu.parkerlabel",
        info_plist={
            "CFBundleDisplayName": "ParkerLabel",
            "CFBundleShortVersionString": app_version,
            "CFBundleVersion": app_version,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
        },
    )
else:
    from builds.prune_windows_bundle import filtered_toc

    a.binaries = filtered_toc(a.binaries)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="ParkerLabel",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=str(app_icon_ico),
    )

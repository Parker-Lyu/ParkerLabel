import logging
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from runtime_paths import (
    PortableLocationError,
    application_icon_path,
    model_directory,
    model_manifest_path,
    prepare_runtime,
)


def bundled_model_errors():
    from parker_label_app.model_manager import load_manifest, missing_models

    manifest = load_manifest(model_manifest_path())
    return [entry["path"].split("/", 1)[-1] for entry in missing_models(manifest, model_directory())]


def main():
    """Start the desktop annotation application."""
    if "--runtime-self-test" in sys.argv:
        import cv2
        import numpy
        import onnxruntime

        if not cv2.__version__ or not numpy.__version__ or not onnxruntime.__version__:
            return 1
        if getattr(sys, "frozen", False):
            invalid = bundled_model_errors()
            if invalid:
                print(f"Missing or invalid bundled models: {', '.join(invalid)}", file=sys.stderr)
                return 1
            for filename in ("encoder.onnx", "decoder.onnx"):
                onnxruntime.InferenceSession(
                    str(model_directory() / filename), providers=["CPUExecutionProvider"]
                )
        return 0
    app = QApplication(sys.argv)
    app.setApplicationName("ParkerLabel")
    app.setWindowIcon(QIcon(str(application_icon_path())))
    try:
        prepare_runtime()
        from parker_label_app import MainWindow
        from parker_label_app.app_info import APP_NAME
        from parker_label_app.i18n import language_manager
        from parker_label_app.model_download_dialog import ensure_runtime_models

        app.setApplicationName(APP_NAME)
        if getattr(sys, "frozen", False):
            invalid = bundled_model_errors()
            if invalid:
                raise RuntimeError(
                    language_manager.text("model.bundled_invalid", files=", ".join(invalid))
                )
        elif not ensure_runtime_models():
            return 1
        window = MainWindow()
    except PortableLocationError as error:
        from parker_label_app.i18n import startup_text

        key = "error.app_translocated" if error.translocated else "error.portable_directory_unavailable"
        QMessageBox.critical(
            None,
            startup_text("app.start_failed"),
            startup_text(key, path=str(error.directory)),
        )
        return 1
    except Exception as error:
        logging.getLogger("parker_label").exception("Startup failed")
        title = (
            language_manager.text("app.start_failed")
            if "language_manager" in locals()
            else "ParkerLabel"
        )
        QMessageBox.critical(None, title, str(error))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

import logging
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from runtime_paths import application_icon_path, prepare_runtime


def main():
    """Start the desktop annotation application."""
    app = QApplication(sys.argv)
    app.setApplicationName("ParkerLabel")
    app.setWindowIcon(QIcon(str(application_icon_path())))
    if "--runtime-self-test" in sys.argv:
        import cv2
        import numpy
        import onnxruntime

        if not cv2.__version__ or not numpy.__version__ or not onnxruntime.__version__:
            return 1
        return 0
    try:
        prepare_runtime()
        from parker_label_app import MainWindow
        from parker_label_app.app_info import APP_NAME
        from parker_label_app.i18n import language_manager
        from parker_label_app.model_download_dialog import ensure_runtime_models

        app.setApplicationName(APP_NAME)
        if not ensure_runtime_models():
            return 1
        window = MainWindow()
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

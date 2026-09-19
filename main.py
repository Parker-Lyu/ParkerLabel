import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from parker_label_app import MainWindow
from parker_label_app.app_info import APP_NAME
from parker_label_app.i18n import language_manager


def main():
    """Start the desktop annotation application."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    try:
        window = MainWindow()
    except Exception as error:
        QMessageBox.critical(None, language_manager.text("app.start_failed"), str(error))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

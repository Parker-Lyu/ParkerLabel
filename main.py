import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from parker_label_app import MainWindow


def main():
    """Start the desktop annotation application."""
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
    except Exception as error:
        QMessageBox.critical(None, "启动失败", str(error))
        return 1
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

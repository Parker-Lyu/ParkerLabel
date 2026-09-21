import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from parker_label_app.update_checker import ReleaseInfo, UpdateResult
from parker_label_app.update_dialog import UpdateCheckDialog


class FakeChecker(QObject):
    checking = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.starts = 0

    def start(self):
        if self.running:
            return False
        self.running = True
        self.starts += 1
        return True


class UpdateDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.opened = []
        self.checker = FakeChecker()
        self.dialog = UpdateCheckDialog(None, self.opened.append, self.checker)

    def tearDown(self):
        self.checker.running = False
        self.dialog.close()

    def test_checking_source_and_update_result(self):
        self.assertTrue(self.dialog.start())
        self.assertFalse(self.dialog.start())
        self.checker.checking.emit("gitee")
        self.assertIn("Gitee", self.dialog.status_label.text())

        release = ReleaseInfo("0.10.0", (0, 10, 0), "Changes", "gitee")
        self.checker.running = False
        self.checker.completed.emit(UpdateResult("0.9.0", release, "gitee"))

        self.assertTrue(self.dialog.github_button.isVisibleTo(self.dialog))
        self.assertTrue(self.dialog.gitee_button.isVisibleTo(self.dialog))
        self.assertEqual(self.dialog.notes.toPlainText(), "Changes")
        self.dialog.github_button.click()
        self.dialog.gitee_button.click()
        self.assertEqual(len(self.opened), 2)

    def test_latest_and_failure_are_distinct_states(self):
        self.checker.completed.emit(UpdateResult("0.9.0", None, "github"))
        latest_text = self.dialog.status_label.text()
        self.assertFalse(self.dialog.github_button.isVisibleTo(self.dialog))

        self.checker.failed.emit("network offline")
        self.assertNotEqual(self.dialog.status_label.text(), latest_text)
        self.assertIn("network offline", self.dialog.version_label.text())


if __name__ == "__main__":
    unittest.main()

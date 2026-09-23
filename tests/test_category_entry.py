import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from parker_label_app.models import AnnotationDocument, Segment
import parker_label_app.window as window_module


class CategoryEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        settings = QSettings(
            str(Path(self.directory.name) / "window.ini"), QSettings.IniFormat
        )
        with patch.object(window_module, "portable_settings", return_value=settings), patch.object(
            window_module, "SegmentationEngine", return_value=object()
        ):
            self.window = window_module.MainWindow()
        first = self.window.categories[0]
        self.second = self.window.categories[1]
        self.window.document = AnnotationDocument(
            Path(self.directory.name) / "image.png",
            np.zeros((20, 20, 3), dtype=np.uint8),
            (20, 20),
            segments=[Segment(first.id, first.name, 255)],
        )
        self.window.current_index = 0
        self.window.refresh_table()
        self.window.show()
        self.app.processEvents()
        self.combo = self.window.table.cellWidget(0, self.window.COL_CATEGORY)
        self.editor = self.combo.lineEdit()

    def tearDown(self):
        self.window.document = None
        self.window.close()
        self.app.processEvents()
        self.directory.cleanup()

    def type_category(self, name):
        self.editor.setFocus()
        self.editor.selectAll()
        QTest.keyClicks(self.editor, name)
        self.app.processEvents()

    def test_enter_accepts_existing_category_and_ends_editing(self):
        self.type_category(self.second.name)
        self.assertNotEqual(self.window.document.segments[0].category_name, self.second.name)
        QTest.keyClick(self.editor, Qt.Key_Return)
        self.app.processEvents()
        self.assertEqual(self.window.document.segments[0].category_name, self.second.name)
        self.assertFalse(self.editor.hasFocus())

    def test_enter_warns_for_missing_category_without_changing_segment(self):
        original = self.window.document.segments[0].category_name
        self.type_category("not-a-category")
        with patch.object(self.window, "show_warning") as warning:
            QTest.keyClick(self.editor, Qt.Key_Return)
            self.app.processEvents()
        self.assertEqual(self.window.document.segments[0].category_name, original)
        warning.assert_called_once_with(
            self.window.t("table.category_missing_title"),
            self.window.t("table.category_missing", name="not-a-category"),
        )
        self.assertEqual(self.combo.findText("not-a-category"), -1)

    def test_dropdown_selection_still_updates_category(self):
        position = self.combo.findText(self.second.name)
        self.combo.setCurrentIndex(position)
        self.combo.activated[str].emit(self.second.name)
        self.assertEqual(self.window.document.segments[0].category_name, self.second.name)


if __name__ == "__main__":
    unittest.main()

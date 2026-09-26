import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication, QCheckBox

from parker_label_app.models import AnnotationDocument, Segment
import parker_label_app.window as window_module


class IscrowdTableTests(unittest.TestCase):
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
        category = self.window.categories[0]
        mask = np.ones((20, 20), dtype=np.uint8)
        self.window.document = AnnotationDocument(
            Path(self.directory.name) / "image.png",
            np.zeros((20, 20, 3), dtype=np.uint8),
            (20, 20),
            segments=[
                Segment(category.id, category.name, 255, mask=mask),
                Segment(category.id, category.name, 256, mask=mask),
            ],
        )
        self.window.current_index = 0
        self.window.refresh_table()

    def tearDown(self):
        self.window.document = None
        self.window.close()
        self.directory.cleanup()

    def checkbox(self, row):
        return self.window.table.cellWidget(
            row, self.window.COL_ISCROWD
        ).findChild(QCheckBox)

    def test_checkbox_requires_selected_target_and_commit(self):
        self.assertEqual(self.window.table.columnCount(), 7)
        self.assertFalse(self.checkbox(0).isChecked())
        self.assertTrue(self.checkbox(0).isEnabled())
        self.assertFalse(self.checkbox(1).isEnabled())
        self.checkbox(0).click()
        self.assertEqual(self.window.document.segments[0].iscrowd, 1)
        self.assertTrue(self.window.has_pending_target_edit())
        self.window.undo_edit()
        self.assertEqual(self.window.document.segments[0].iscrowd, 0)
        self.assertFalse(self.window.has_pending_target_edit())
        self.window.redo_edit()
        self.assertEqual(self.window.document.segments[0].iscrowd, 1)
        self.window.discard_edit()
        self.assertEqual(self.window.document.segments[0].iscrowd, 0)
        self.assertFalse(self.window.document.dirty)
        self.checkbox(0).click()
        self.assertTrue(self.window.commit_current_segment())
        self.assertEqual(self.window.document.segments[0].iscrowd, 1)
        self.assertFalse(self.window.has_pending_target_edit())
        self.assertTrue(self.window.document.dirty)


if __name__ == "__main__":
    unittest.main()

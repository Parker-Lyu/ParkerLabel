import tempfile
import unittest
from pathlib import Path

from PyQt5.QtCore import QSettings

from parker_label_app.i18n import LanguageManager


class LanguageManagerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QSettings(
            str(Path(self.directory.name) / "settings.ini"), QSettings.IniFormat
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_first_launch_defaults_to_english(self):
        self.assertEqual(LanguageManager(self.settings).language, "en_US")

    def test_saved_language_is_preserved(self):
        self.settings.setValue("interface/language", "zh_CN")
        self.assertEqual(LanguageManager(self.settings).language, "zh_CN")

    def test_invalid_language_falls_back_to_english(self):
        self.settings.setValue("interface/language", "unsupported")
        self.assertEqual(LanguageManager(self.settings).language, "en_US")

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtCore import QSettings

import parker_label_app.i18n as i18n
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

    def test_startup_error_uses_system_language_until_user_selects_one(self):
        with patch.object(i18n, "language_manager", LanguageManager(self.settings)), patch.object(
            i18n.QLocale, "system"
        ) as system_locale:
            system_locale.return_value.name.return_value = "zh_CN"
            self.assertIn("解压后的整个", i18n.startup_text("error.app_translocated"))
            self.settings.setValue("interface/language", "ja_JP")
            with patch.object(i18n, "language_manager", LanguageManager(self.settings)):
                self.assertIn("フォルダー全体", i18n.startup_text("error.app_translocated"))

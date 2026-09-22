import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QSettings, Qt, QTimer, QUrlQuery
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QAction, QApplication, QComboBox, QLabel, QLineEdit, QPushButton

from parker_label_app.app_info import APP_VERSION, GITEE_REPOSITORY_URL, source_code_url
from parker_label_app.i18n import LANGUAGE_NAMES, _TEXT, language_manager
from parker_label_app.shortcut_dialog import ShortcutSettingsDialog
from parker_label_app.shortcuts import (
    ShortcutStore,
    native_sequence,
    reserved_reason,
    validate_config,
)
import parker_label_app.window as window_module


class ShortcutStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QSettings(
            str(Path(self.directory.name) / "shortcuts.ini"), QSettings.IniFormat
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_platform_defaults_use_command_on_macos(self):
        mac = ShortcutStore(self.settings, is_macos=True).defaults()
        windows = ShortcutStore(self.settings, is_macos=False).defaults()
        self.assertEqual(mac["mode_smart"], "Q")
        self.assertEqual(mac["mode_brush"], "W")
        self.assertEqual(mac["mode_query"], "E")
        self.assertEqual(mac["open_image"], "Ctrl+O")
        self.assertEqual(mac["redo_edit"], "Ctrl+Shift+Z")
        self.assertEqual(windows["redo_edit"], "Ctrl+Y")
        self.assertEqual(validate_config(mac, True), {})
        self.assertEqual(validate_config(windows, False), {})
        if os.sys.platform == "darwin":
            self.assertEqual(native_sequence(mac["open_image"]), "⌘O")

    def test_conflict_and_reserved_shortcuts(self):
        config = ShortcutStore(self.settings, is_macos=True).defaults()
        config["add_target"] = "Q"
        errors = validate_config(config, True)
        self.assertIn("add_target", errors)
        self.assertIn("mode_smart", errors)
        config["add_target"] = "Ctrl+C"
        self.assertEqual(
            validate_config(config, True)["add_target"],
            "shortcut.error.reserved_system",
        )
        self.assertEqual(reserved_reason("Return", True), "shortcut.error.reserved_basic")

    def test_clear_and_corrupt_settings_survive_restart(self):
        store = ShortcutStore(self.settings, is_macos=True)
        config = store.defaults()
        config["add_target"] = ""
        config["mode_smart"] = "R"
        store.save(config)
        self.assertEqual(ShortcutStore(self.settings, True).load(), config)
        self.settings.setValue("shortcuts/mode_smart", "Ctrl+Q")
        recovered = ShortcutStore(self.settings, True)
        self.assertEqual(recovered.load()["mode_smart"], "Q")
        self.assertIn("mode_smart", recovered.warnings)
        self.assertEqual(recovered.load()["add_target"], "")


class ShortcutWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QSettings(
            str(Path(self.directory.name) / "window.ini"), QSettings.IniFormat
        )
        with patch.object(window_module, "portable_settings", return_value=self.settings), patch.object(
            window_module, "SegmentationEngine", return_value=object()
        ):
            self.window = window_module.MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.shortcut_manager.set_recording(False)
        self.window.close()
        self.app.processEvents()
        self.directory.cleanup()

    def test_primary_grid_and_localized_menus(self):
        buttons = (
            self.window.open_button,
            self.window.quality_button,
            self.window.category_button,
            self.window.save_button,
        )
        self.assertEqual(len({button.width() for button in buttons}), 1)
        self.assertEqual(len({button.height() for button in buttons}), 1)
        self.assertEqual(buttons[0].y(), buttons[1].y())
        self.assertEqual(buttons[2].y(), buttons[3].y())
        self.assertLess(buttons[0].y(), buttons[2].y())
        self.assertFalse(hasattr(self.window, "language_button"))
        self.assertFalse(hasattr(self.window, "tooltip_button"))
        self.assertEqual(
            self.window.settings_menu.title(), self.window.t("menu.settings")
        )
        self.assertEqual(
            self.window.shortcut_settings_action.menuRole(), QAction.NoRole
        )
        self.assertEqual(self.window.about_action.menuRole(), QAction.NoRole)
        self.assertEqual(self.window.check_updates_action.menuRole(), QAction.NoRole)
        self.assertEqual(self.window.licenses_action.menuRole(), QAction.NoRole)
        self.assertIn(
            self.window.shortcut_settings_action, self.window.settings_menu.actions()
        )
        self.assertIn(self.window.about_action, self.window.help_menu.actions())
        self.assertIn(self.window.check_updates_action, self.window.help_menu.actions())
        self.assertIn(self.window.licenses_action, self.window.help_menu.actions())
        for code in LANGUAGE_NAMES:
            self.assertIn("shortcut.title", _TEXT[code])
            self.assertIn("menu.settings", _TEXT[code])
            self.assertIn("menu.gitee", _TEXT[code])
            self.assertIn("menu.check_updates", _TEXT[code])
            self.assertIn("menu.licenses", _TEXT[code])
            self.assertIn("update.open_github", _TEXT[code])
            self.assertIn(code, [a.data() for a in self.window.language_actions.actions()])

    def test_about_dialog_contains_gitee_repository_link(self):
        dialog_text = []
        button_text = []

        def capture_dialog():
            dialog = self.app.activeModalWidget()
            dialog_text.extend(label.text() for label in dialog.findChildren(QLabel))
            button_text.extend(button.text() for button in dialog.findChildren(QPushButton))
            dialog.accept()

        QTimer.singleShot(0, capture_dialog)
        self.window.show_about_dialog()

        self.assertTrue(
            any(GITEE_REPOSITORY_URL in text for text in dialog_text), dialog_text
        )
        self.assertIn(self.window.t("menu.check_updates"), button_text)
        self.assertIn(self.window.t("menu.licenses"), button_text)

    @patch.object(window_module.QDesktopServices, "openUrl", return_value=True)
    def test_open_source_licenses_uses_local_bundled_notice(self, open_url):
        self.window.open_source_licenses()
        url = open_url.call_args.args[0]
        self.assertTrue(url.isLocalFile())
        self.assertTrue(url.toLocalFile().endswith("third_party_licenses/OPEN_SOURCE_LICENSES.html"))
        query = QUrlQuery(url)
        self.assertEqual(query.queryItemValue("version"), APP_VERSION or self.window.t("about.development_build"))
        self.assertEqual(query.queryItemValue("source"), source_code_url())
        platform_value = query.queryItemValue("platform")
        if window_module.sys.platform in {"darwin", "win32"}:
            self.assertTrue(platform_value.startswith(("macos-", "windows-")))
        else:
            self.assertEqual(platform_value, "")

    def test_offline_license_page_has_required_entries(self):
        page = (
            Path(window_module.resource_root())
            / "third_party_licenses"
            / "OPEN_SOURCE_LICENSES.html"
        ).read_text(encoding="utf-8")
        for text in (
            "ParkerLabel",
            "GPL-3.0-only",
            "Third-party components",
            "MobileSAM",
            "Segment Anything",
            "TinyViT",
            "Model source",
            "Source code for this version",
            "Complete license files",
            "../LICENSE",
            "THIRD_PARTY_NOTICES.md",
        ):
            self.assertIn(text, page)

    def test_shortcuts_dispatch_and_text_input_is_protected(self):
        called = []
        self.window.shortcut_manager.bind("mode_smart", lambda: called.append("smart"))
        self.window.shortcut_manager.bind("open_image", lambda: called.append("open"))
        QTest.keyClick(self.window, Qt.Key_Q)
        QTest.keyClick(self.window, Qt.Key_O, Qt.ControlModifier)
        self.assertEqual(called, ["smart", "open"])
        edit = QLineEdit(self.window)
        edit.show()
        edit.setFocus()
        self.app.processEvents()
        QTest.keyClicks(edit, "q")
        self.assertEqual(edit.text(), "q")
        self.assertEqual(called, ["smart", "open"])
        edit.close()

        combo = QComboBox(self.window)
        combo.addItems(["Query", "Quality"])
        combo.show()
        combo.setFocus()
        self.app.processEvents()
        QTest.keyClick(combo, Qt.Key_Q)
        self.assertEqual(called, ["smart", "open"])
        combo.close()

    def test_recording_suppresses_actions_and_closing_clears_state(self):
        called = []
        self.window.shortcut_manager.bind("mode_smart", lambda: called.append("smart"))
        dialog = ShortcutSettingsDialog(self.window, self.window.shortcut_manager)
        dialog.open()
        self.app.processEvents()
        dialog.begin_recording("add_target")
        QTest.keyClick(dialog, Qt.Key_Q)
        self.assertEqual(called, [])
        self.assertEqual(dialog.draft["add_target"], "Q")
        dialog.begin_recording("add_target")
        dialog.close()
        self.app.processEvents()
        self.assertFalse(self.window.shortcut_manager.recording)

    def test_language_change_updates_menus_without_changing_bindings(self):
        original_language = language_manager.language
        original_bindings = dict(self.window.shortcut_manager.config)
        next_language = "en_US" if original_language != "en_US" else "zh_CN"
        with patch.object(language_manager, "settings", self.settings):
            try:
                language_manager.set_language(next_language)
                self.assertEqual(self.window.settings_menu.title(), _TEXT[next_language]["menu.settings"])
                self.assertEqual(self.window.help_menu.title(), _TEXT[next_language]["menu.help"])
                self.assertEqual(self.window.shortcut_manager.config, original_bindings)
            finally:
                language_manager.set_language(original_language)

    def test_primary_buttons_fit_all_languages(self):
        original_language = language_manager.language
        with patch.object(language_manager, "settings", self.settings):
            try:
                for code in LANGUAGE_NAMES:
                    language_manager.set_language(code)
                    self.app.processEvents()
                    buttons = (
                        self.window.open_button,
                        self.window.quality_button,
                        self.window.category_button,
                        self.window.save_button,
                    )
                    self.assertEqual(len({button.width() for button in buttons}), 1)
                    for button in buttons:
                        self.assertGreaterEqual(button.width(), button.sizeHint().width())
                    self.assertLessEqual(
                        self.window.category_config_label.width(),
                        self.window.control_panel.width(),
                    )
            finally:
                language_manager.set_language(original_language)

    def test_dialog_cancel_save_restore_and_conflict(self):
        dialog = ShortcutSettingsDialog(self.window, self.window.shortcut_manager)
        original = dialog.draft["add_target"]
        dialog.draft["add_target"] = "Q"
        dialog.validate()
        self.assertFalse(dialog.save_button.isEnabled())
        dialog.draft["add_target"] = "R"
        dialog.validate()
        self.assertTrue(dialog.save_button.isEnabled())
        dialog.reject()
        self.assertEqual(self.window.shortcut_manager.config["add_target"], original)
        dialog = ShortcutSettingsDialog(self.window, self.window.shortcut_manager)
        dialog.draft["add_target"] = "R"
        dialog.validate()
        dialog.save()
        self.assertEqual(self.window.shortcut_manager.config["add_target"], "R")
        self.assertEqual(ShortcutStore(self.settings, is_macos=os.sys.platform == "darwin").load()["add_target"], "R")
        dialog = ShortcutSettingsDialog(self.window, self.window.shortcut_manager)
        dialog.restore_all_defaults()
        dialog.save()
        self.assertEqual(self.window.shortcut_manager.config["add_target"], original)


if __name__ == "__main__":
    unittest.main()

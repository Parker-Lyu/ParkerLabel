import sys
from dataclasses import dataclass

from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTextEdit,
)


UNBOUND = ""
SETTINGS_PREFIX = "shortcuts/"


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    text_key: str
    group_key: str
    scope_key: str
    mac_default: str = ""
    windows_default: str = ""
    repeat: bool = False
    disruptive: bool = False

    def default(self, is_macos=None):
        if is_macos is None:
            is_macos = sys.platform == "darwin"
        return self.mac_default if is_macos else self.windows_default


ACTION_SPECS = (
    ActionSpec("open_image", "shortcut.action.open_image", "shortcut.group.file", "shortcut.scope.main", "Ctrl+O", "Ctrl+O", disruptive=True),
    ActionSpec("save_document", "shortcut.action.save_document", "shortcut.group.file", "shortcut.scope.main", "Ctrl+S", "Ctrl+S", disruptive=True),
    ActionSpec("shortcut_settings", "shortcut.action.shortcut_settings", "shortcut.group.file", "shortcut.scope.main", "Ctrl+,", "Ctrl+,", disruptive=True),
    ActionSpec("undo_edit", "shortcut.action.undo_edit", "shortcut.group.target", "shortcut.scope.workspace", "Ctrl+Z", "Ctrl+Z", disruptive=True),
    ActionSpec("redo_edit", "shortcut.action.redo_edit", "shortcut.group.target", "shortcut.scope.workspace", "Ctrl+Shift+Z", "Ctrl+Y", disruptive=True),
    ActionSpec("add_target", "shortcut.action.add_target", "shortcut.group.target", "shortcut.scope.workspace", "A", "A", disruptive=True),
    ActionSpec("commit_target", "shortcut.action.commit_target", "shortcut.group.target", "shortcut.scope.workspace", "Ctrl+Return", "Ctrl+Return", disruptive=True),
    ActionSpec("discard_edit", "shortcut.action.discard_edit", "shortcut.group.target", "shortcut.scope.workspace", "", "", disruptive=True),
    ActionSpec("delete_target", "shortcut.action.delete_target", "shortcut.group.target", "shortcut.scope.workspace", "", "", disruptive=True),
    ActionSpec("mode_smart", "shortcut.action.mode_smart", "shortcut.group.mode", "shortcut.scope.workspace", "Q", "Q", disruptive=True),
    ActionSpec("mode_brush", "shortcut.action.mode_brush", "shortcut.group.mode", "shortcut.scope.workspace", "W", "W", disruptive=True),
    ActionSpec("mode_query", "shortcut.action.mode_query", "shortcut.group.mode", "shortcut.scope.workspace", "E", "E", disruptive=True),
    ActionSpec("view_image", "shortcut.action.view_image", "shortcut.group.view", "shortcut.scope.workspace", "1", "1"),
    ActionSpec("view_mask", "shortcut.action.view_mask", "shortcut.group.view", "shortcut.scope.workspace", "2", "2"),
    ActionSpec("view_overlay", "shortcut.action.view_overlay", "shortcut.group.view", "shortcut.scope.workspace", "3", "3"),
    ActionSpec("brush_smaller", "shortcut.action.brush_smaller", "shortcut.group.brush", "shortcut.scope.workspace", "[", "[", repeat=True),
    ActionSpec("brush_larger", "shortcut.action.brush_larger", "shortcut.group.brush", "shortcut.scope.workspace", "]", "]", repeat=True),
    ActionSpec("erode", "shortcut.action.erode", "shortcut.group.brush", "shortcut.scope.workspace", disruptive=True),
    ActionSpec("dilate", "shortcut.action.dilate", "shortcut.group.brush", "shortcut.scope.workspace", disruptive=True),
    ActionSpec("toggle_quality", "shortcut.action.toggle_quality", "shortcut.group.other", "shortcut.scope.main"),
    ActionSpec("category_config", "shortcut.action.category_config", "shortcut.group.other", "shortcut.scope.main", disruptive=True),
)
SPECS_BY_ID = {spec.action_id: spec for spec in ACTION_SPECS}


def normalize_sequence(value):
    if not value:
        return ""
    sequence = QKeySequence(value)
    if sequence.count() != 1:
        return ""
    return sequence.toString(QKeySequence.PortableText)


def native_sequence(value):
    if not value:
        return ""
    return QKeySequence(value).toString(QKeySequence.NativeText)


def sequence_from_key_event(event):
    key = event.key()
    if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
        return ""
    combined = int(event.modifiers()) | key
    return normalize_sequence(QKeySequence(combined).toString(QKeySequence.PortableText))


def reserved_reason(sequence, is_macos=None):
    sequence = normalize_sequence(sequence)
    if not sequence:
        return None
    if is_macos is None:
        is_macos = sys.platform == "darwin"
    banned = {"Esc", "Tab", "Return", "Enter"}
    if sequence in banned:
        return "shortcut.error.reserved_basic"
    common = {"Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+A"}
    mac = common | {"Ctrl+Q", "Ctrl+H", "Ctrl+M", "Ctrl+Tab", "Meta+Tab"}
    windows = {"Alt+F4", "Alt+Tab", "Ctrl+Alt+Delete"}
    if sequence in (mac if is_macos else common | windows):
        return "shortcut.error.reserved_system"
    return None


def validate_config(config, is_macos=None):
    errors = {}
    owners = {}
    for spec in ACTION_SPECS:
        value = normalize_sequence(config.get(spec.action_id, ""))
        if config.get(spec.action_id, "") and not value:
            errors[spec.action_id] = "shortcut.error.invalid"
            continue
        reason = reserved_reason(value, is_macos)
        if reason:
            errors[spec.action_id] = reason
            continue
        if value:
            if value in owners:
                other = owners[value]
                errors[spec.action_id] = ("shortcut.error.conflict", other)
                errors[other] = ("shortcut.error.conflict", spec.action_id)
            else:
                owners[value] = spec.action_id
    return errors


class ShortcutStore:
    def __init__(self, settings, is_macos=None):
        self.settings = settings
        self.is_macos = sys.platform == "darwin" if is_macos is None else is_macos
        self.warnings = []

    def defaults(self):
        return {spec.action_id: normalize_sequence(spec.default(self.is_macos)) for spec in ACTION_SPECS}

    def load(self):
        config = {}
        used = set()
        defaults = self.defaults()
        self.warnings = []
        for spec in ACTION_SPECS:
            key = SETTINGS_PREFIX + spec.action_id
            raw = self.settings.value(key, None)
            candidate = defaults[spec.action_id] if raw is None else str(raw)
            normalized = normalize_sequence(candidate)
            if candidate and (not normalized or reserved_reason(normalized, self.is_macos) or normalized in used):
                fallback = defaults[spec.action_id]
                fallback = normalize_sequence(fallback)
                if fallback and not reserved_reason(fallback, self.is_macos) and fallback not in used:
                    normalized = fallback
                else:
                    normalized = ""
                self.warnings.append(spec.action_id)
            config[spec.action_id] = normalized
            if normalized:
                used.add(normalized)
        return config

    def save(self, config):
        errors = validate_config(config, self.is_macos)
        if errors:
            raise ValueError("invalid shortcut configuration")
        previous = {
            spec.action_id: (
                self.settings.contains(SETTINGS_PREFIX + spec.action_id),
                self.settings.value(SETTINGS_PREFIX + spec.action_id, None),
            )
            for spec in ACTION_SPECS
        }
        for spec in ACTION_SPECS:
            self.settings.setValue(SETTINGS_PREFIX + spec.action_id, normalize_sequence(config[spec.action_id]))
        self.settings.sync()
        if self.settings.status() != self.settings.NoError:
            for spec in ACTION_SPECS:
                exists, value = previous[spec.action_id]
                key = SETTINGS_PREFIX + spec.action_id
                if exists:
                    self.settings.setValue(key, value)
                else:
                    self.settings.remove(key)
            self.settings.sync()
            raise OSError("QSettings sync failed")


class ShortcutManager(QObject):
    def __init__(self, host, store):
        super().__init__(host)
        self.host = host
        self.store = store
        self.config = store.load()
        self.bindings = {}
        self.recording = False
        self.ime_composing = False
        self.ime_widget = None
        QApplication.instance().installEventFilter(self)

    def bind(self, action_id, callback, enabled=lambda: True):
        self.bindings[action_id] = (callback, enabled)

    def apply(self, config):
        self.config = dict(config)

    def set_recording(self, recording):
        self.recording = recording

    def dispose(self):
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def shortcut_text(self, action_id, native=True):
        value = self.config.get(action_id, "")
        return native_sequence(value) if native else value

    def _target_blocks_shortcuts(self, target):
        if target is None:
            return False
        if isinstance(target, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)):
            return True
        if isinstance(target, QTableWidget) and target.state() == QAbstractItemView.EditingState:
            return True
        parent = target.parentWidget() if hasattr(target, "parentWidget") else None
        while parent is not None:
            if isinstance(parent, (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox)):
                return True
            if isinstance(parent, QTableWidget) and parent.state() == QAbstractItemView.EditingState:
                return True
            parent = parent.parentWidget()
        return False

    def eventFilter(self, watched, event):
        if event.type() == QEvent.InputMethod:
            self.ime_composing = bool(event.preeditString())
            self.ime_widget = watched if self.ime_composing else None
            return False
        if event.type() == QEvent.FocusOut and watched is self.ime_widget:
            self.ime_composing = False
            self.ime_widget = None
            return False
        if event.type() != QEvent.KeyPress or self.recording:
            return False
        if QApplication.activeModalWidget() is not None:
            return False
        if QApplication.activePopupWidget() is not None:
            return False
        if self._target_blocks_shortcuts(QApplication.focusWidget()):
            return False
        sequence = sequence_from_key_event(event)
        if not sequence:
            return False
        if self.ime_composing and "+" not in sequence:
            return False
        for spec in ACTION_SPECS:
            if self.config.get(spec.action_id) != sequence:
                continue
            if event.isAutoRepeat() and not spec.repeat:
                return True
            if spec.disruptive and (getattr(self.host, "painting", None) is not None or getattr(self.host, "panning", False)):
                return True
            binding = self.bindings.get(spec.action_id)
            if binding is None:
                return True
            callback, enabled = binding
            if enabled():
                callback()
            return True
        return False

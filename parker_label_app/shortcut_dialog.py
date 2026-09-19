from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .shortcuts import (
    ACTION_SPECS,
    SPECS_BY_ID,
    native_sequence,
    normalize_sequence,
    sequence_from_key_event,
    validate_config,
)


class ShortcutSettingsDialog(QDialog):
    COL_ACTION = 0
    COL_SHORTCUT = 1
    COL_SCOPE = 2
    COL_CLEAR = 3
    COL_DEFAULT = 4

    def __init__(self, window, manager):
        super().__init__(window)
        self.window = window
        self.manager = manager
        self.store = manager.store
        self.original = dict(manager.config)
        self.draft = dict(self.original)
        self.recording_id = None
        self.row_for_action = {}
        self.group_rows = {}
        self.setModal(True)
        self.setWindowTitle(self.window.t("shortcut.title"))
        self.resize(760, 560)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.window.t("shortcut.search"))
        self.search.textChanged.connect(self.apply_filter)
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(
            [
                self.window.t("shortcut.column.action"),
                self.window.t("shortcut.column.current"),
                self.window.t("shortcut.column.scope"),
                "",
                "",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self.cell_clicked)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.restore_all = QPushButton(self.window.t("shortcut.restore_all"), self)
        self.cancel_button = QPushButton(self.window.t("common.cancel"), self)
        self.save_button = QPushButton(self.window.t("common.save"), self)
        self.restore_all.clicked.connect(self.restore_all_defaults)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.save)
        buttons = QHBoxLayout()
        buttons.addWidget(self.restore_all)
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        self.populate()
        self.validate()

    def populate(self):
        self.table.setRowCount(0)
        current_group = None
        for spec in ACTION_SPECS:
            if spec.group_key != current_group:
                current_group = spec.group_key
                row = self.table.rowCount()
                self.table.insertRow(row)
                item = QTableWidgetItem(self.window.t(current_group))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                self.table.setItem(row, 0, item)
                self.table.setSpan(row, 0, 1, 5)
                self.group_rows[current_group] = row
            row = self.table.rowCount()
            self.table.insertRow(row)
            action = QTableWidgetItem(self.window.t(spec.text_key))
            action.setData(Qt.UserRole, spec.action_id)
            self.table.setItem(row, self.COL_ACTION, action)
            self.table.setItem(row, self.COL_SHORTCUT, QTableWidgetItem())
            self.table.setItem(row, self.COL_SCOPE, QTableWidgetItem(self.window.t(spec.scope_key)))
            clear = QPushButton(self.window.t("shortcut.clear"), self.table)
            reset = QPushButton(self.window.t("shortcut.restore_one"), self.table)
            clear.clicked.connect(lambda _=False, action_id=spec.action_id: self.clear_binding(action_id))
            reset.clicked.connect(lambda _=False, action_id=spec.action_id: self.restore_default(action_id))
            self.table.setCellWidget(row, self.COL_CLEAR, clear)
            self.table.setCellWidget(row, self.COL_DEFAULT, reset)
            self.row_for_action[spec.action_id] = row
        self.refresh_rows()
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(False)

    def refresh_rows(self):
        for spec in ACTION_SPECS:
            row = self.row_for_action[spec.action_id]
            item = self.table.item(row, self.COL_SHORTCUT)
            value = self.draft[spec.action_id]
            item.setText(native_sequence(value) if value else self.window.t("shortcut.unbound"))
            item.setToolTip("")
            item.setForeground(QBrush())

    def cell_clicked(self, row, column):
        if column != self.COL_SHORTCUT:
            return
        action = self.table.item(row, self.COL_ACTION)
        if action is None:
            return
        action_id = action.data(Qt.UserRole)
        if action_id:
            self.begin_recording(action_id)

    def begin_recording(self, action_id):
        if self.recording_id is not None:
            self.finish_recording()
        self.recording_id = action_id
        self.manager.set_recording(True)
        QApplication.instance().installEventFilter(self)
        row = self.row_for_action[action_id]
        self.table.item(row, self.COL_SHORTCUT).setText(self.window.t("shortcut.recording"))
        self.status.setText(self.window.t("shortcut.recording_hint"))

    def finish_recording(self):
        QApplication.instance().removeEventFilter(self)
        self.manager.set_recording(False)
        self.recording_id = None

    def eventFilter(self, watched, event):
        if self.recording_id is None:
            return False
        if event.type() == QEvent.MouseButtonPress and watched is not self.table.viewport():
            self.finish_recording()
            self.refresh_rows()
            self.validate()
            return False
        if event.type() != QEvent.KeyPress:
            return False
        if event.key() == Qt.Key_Escape:
            self.finish_recording()
            self.refresh_rows()
            self.validate()
            return True
        sequence = sequence_from_key_event(event)
        if not sequence:
            return True
        self.draft[self.recording_id] = normalize_sequence(sequence)
        self.finish_recording()
        self.refresh_rows()
        self.validate()
        return True

    def clear_binding(self, action_id):
        if self.recording_id is not None:
            self.finish_recording()
        self.draft[action_id] = ""
        self.refresh_rows()
        self.validate()

    def restore_default(self, action_id):
        if self.recording_id is not None:
            self.finish_recording()
        self.draft[action_id] = normalize_sequence(SPECS_BY_ID[action_id].default(self.store.is_macos))
        self.refresh_rows()
        self.validate()

    def restore_all_defaults(self):
        if self.recording_id is not None:
            self.finish_recording()
        self.draft = self.store.defaults()
        self.refresh_rows()
        self.validate()

    def validate(self):
        errors = validate_config(self.draft, self.store.is_macos)
        for spec in ACTION_SPECS:
            item = self.table.item(self.row_for_action[spec.action_id], self.COL_SHORTCUT)
            error = errors.get(spec.action_id)
            if not error:
                item.setToolTip("")
                continue
            if isinstance(error, tuple):
                other = SPECS_BY_ID[error[1]]
                message = self.window.t(error[0], action=self.window.t(other.text_key))
            else:
                message = self.window.t(error)
            item.setToolTip(message)
            item.setForeground(QColor("#c62828"))
        if errors:
            first_id, error = next(iter(errors.items()))
            if isinstance(error, tuple):
                other = SPECS_BY_ID[error[1]]
                detail = self.window.t(error[0], action=self.window.t(other.text_key))
            else:
                detail = self.window.t(error)
            self.status.setText(
                self.window.t(
                    "shortcut.validation_failed_detail",
                    action=self.window.t(SPECS_BY_ID[first_id].text_key),
                    error=detail,
                )
            )
        elif self.draft == self.original:
            self.status.setText("")
        else:
            self.status.setText(self.window.t("shortcut.unsaved_changes"))
        self.save_button.setEnabled(not errors and self.draft != self.original)

    def apply_filter(self, text):
        query = text.strip().casefold()
        visible_groups = set()
        for spec in ACTION_SPECS:
            row = self.row_for_action[spec.action_id]
            haystack = " ".join(
                (
                    self.window.t(spec.text_key),
                    native_sequence(self.draft[spec.action_id]),
                    self.draft[spec.action_id],
                )
            ).casefold()
            visible = not query or query in haystack
            self.table.setRowHidden(row, not visible)
            if visible:
                visible_groups.add(spec.group_key)
        for group, row in self.group_rows.items():
            self.table.setRowHidden(row, group not in visible_groups)

    def save(self):
        try:
            self.store.save(self.draft)
        except (OSError, ValueError) as error:
            QMessageBox.warning(
                self,
                self.window.t("shortcut.save_failed"),
                self.window.t("shortcut.save_failed_detail", error=str(error)),
            )
            return
        self.manager.apply(self.draft)
        self.original = dict(self.draft)
        self.window.shortcuts_changed()
        self.accept()

    def reject(self):
        if self.recording_id is not None:
            self.finish_recording()
        super().reject()

    def closeEvent(self, event):
        if self.recording_id is not None:
            self.finish_recording()
        super().closeEvent(event)

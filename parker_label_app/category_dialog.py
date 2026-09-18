from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .category_store import CategoryConfigError, CategoryConfigManager, CategoryStore
from .i18n import language_manager
from .models import Category


class CategoryConfigDialog(QDialog):
    configurationApplied = pyqtSignal(str)

    def __init__(self, manager, active_config_id, apply_validator=None, parent=None):
        """Create a manager for built-in and named user category configurations."""
        super().__init__(parent)
        self.manager = manager
        self.active_config_id = active_config_id
        self.apply_validator = apply_validator
        self.applied_config_id = None
        self.config_id = None
        self.config_name = ""
        self.created_at = ""
        self.parent_version_uuid = None
        self.is_draft = False
        self.draft_saved = False
        self.dirty = False
        self.loading = False
        self.i18n = language_manager
        self.columns = (
            self.t("category.column.enabled"),
            "ID",
            self.t("category.column.name"),
            self.t("category.column.parent"),
            self.t("category.column.description"),
        )
        self.setWindowTitle(self.t("category.title"))
        self.resize(1180, 720)
        self.build_ui()
        self.refresh_config_list(active_config_id)
        self.load_config(active_config_id)

    def t(self, key, **values):
        """Return localized interface text."""
        return self.i18n.text(key, **values)

    def display_config_name(self, config_id, name):
        """Return a localized built-in name without changing stored configuration data."""
        if config_id == CategoryConfigManager.BUILTIN_ID:
            return self.t("category.builtin_name")
        return name

    def build_ui(self):
        """Build configuration actions, list, category table, and dialog actions."""
        new_button = QPushButton(self.t("category.new"))
        self.copy_button = QPushButton(self.t("category.copy"))
        new_button.clicked.connect(self.new_config)
        self.copy_button.clicked.connect(self.copy_config)
        toolbar = QHBoxLayout()
        for button in (new_button, self.copy_button):
            toolbar.addWidget(button)
        toolbar.addStretch(1)

        self.config_list = QListWidget()
        self.config_list.setFixedWidth(310)
        self.config_list.currentItemChanged.connect(self.change_config)

        self.config_title = QLabel()
        self.config_hint = QLabel()
        self.config_hint.setStyleSheet("color: palette(mid)")
        self.uuid_label = QLabel()
        self.uuid_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.created_at_label = QLabel()
        self.created_at_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.parent_version_label = QLabel()
        self.parent_version_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.parent_version_title_label = QLabel(self.t("category.parent_version"))
        heading = QHBoxLayout()
        heading.addWidget(self.config_title)
        heading.addSpacing(12)
        heading.addWidget(self.config_hint)
        heading.addStretch(1)

        identity = QVBoxLayout()
        uuid_row = QHBoxLayout()
        uuid_row.addWidget(QLabel("UUID:"))
        uuid_row.addWidget(self.uuid_label)
        uuid_row.addStretch(1)
        parent_version_row = QHBoxLayout()
        parent_version_row.addWidget(self.parent_version_title_label)
        parent_version_row.addWidget(self.parent_version_label)
        parent_version_row.addStretch(1)
        created_at_row = QHBoxLayout()
        created_at_row.addWidget(QLabel(self.t("category.created_at")))
        created_at_row.addWidget(self.created_at_label)
        created_at_row.addStretch(1)
        identity.addLayout(uuid_row)
        identity.addLayout(parent_version_row)
        identity.addLayout(created_at_row)

        self.table = QTableWidget(0, len(self.columns), self)
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 82)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 170)
        self.table.setColumnWidth(3, 160)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.mark_dirty)

        self.add_entry_button = QPushButton(self.t("category.add_entry"))
        self.delete_entry_button = QPushButton(self.t("category.delete_entry"))
        self.add_entry_button.clicked.connect(self.add_empty_row)
        self.delete_entry_button.clicked.connect(self.delete_selected_rows)
        row_actions = QHBoxLayout()
        row_actions.addWidget(self.add_entry_button)
        row_actions.addWidget(self.delete_entry_button)
        row_actions.addStretch(1)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addLayout(heading)
        editor_layout.addLayout(identity)
        editor_layout.addLayout(row_actions)
        editor_layout.addWidget(self.table)

        content = QHBoxLayout()
        content.addWidget(self.config_list)
        content.addWidget(editor, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.save_button = QPushButton(self.t("common.save"))
        self.apply_button = QPushButton(self.t("category.apply"))
        close_button = QPushButton(self.t("common.close"))
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(close_button)
        self.save_button.clicked.connect(self.save_current)
        self.apply_button.clicked.connect(self.apply_current)
        close_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addLayout(content, 1)
        layout.addLayout(buttons)

    def refresh_config_list(self, selected_id=None):
        """Reload configuration names and status markers."""
        default_id = self.manager.default_config_id()
        self.config_list.blockSignals(True)
        self.config_list.clear()
        selected_item = None
        for config in self.manager.configurations():
            labels = []
            if config.builtin:
                labels.append(self.t("category.status.builtin"))
            if config.id == default_id:
                labels.append(self.t("category.status.default"))
            if config.id == self.active_config_id:
                labels.append(self.t("category.status.active"))
            if self.is_draft and config.id == self.config_id:
                labels.append(self.t("category.status.draft"))
            suffix = f"\n{' · '.join(labels)}" if labels else ""
            display_name = self.display_config_name(config.id, config.name)
            item = QListWidgetItem(f"{display_name}{suffix}")
            item.setData(Qt.UserRole, config.id)
            self.config_list.addItem(item)
            if config.id == selected_id:
                selected_item = item
        self.config_list.setCurrentItem(selected_item)
        self.config_list.blockSignals(False)

    def select_config_in_list(self, config_id):
        """Select a saved configuration without triggering a reload."""
        self.config_list.blockSignals(True)
        self.config_list.clearSelection()
        for row in range(self.config_list.count()):
            item = self.config_list.item(row)
            if item.data(Qt.UserRole) == config_id:
                self.config_list.setCurrentItem(item)
                break
        self.config_list.blockSignals(False)

    def load_config(self, config_id):
        """Load one saved configuration into the editor."""
        config = self.manager.configuration(config_id)
        data = self.manager.load_data(config_id)
        categories = list(data.categories)
        self.config_id = config.id
        self.config_name = config.name
        self.created_at = data.created_at
        self.parent_version_uuid = data.parent_version_uuid
        self.is_draft = False
        self.draft_saved = False
        self.populate(categories)
        self.dirty = False
        self.update_state()

    def change_config(self, current, previous):
        """Resolve edits before selecting another saved configuration."""
        if current is None:
            return
        config_id = current.data(Qt.UserRole)
        if config_id == self.config_id:
            return
        if not self.resolve_unsaved_changes():
            self.select_config_in_list(self.config_id)
            return
        if self.is_draft and self.draft_saved:
            self.manager.freeze(self.config_id)
        try:
            self.load_config(config_id)
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, self.t("category.error"), str(error))
            if previous is not None:
                self.select_config_in_list(previous.data(Qt.UserRole))

    def populate(self, categories):
        """Populate the table with category records."""
        self.loading = True
        self.table.setRowCount(0)
        for category in categories:
            self.append_category(category)
        self.loading = False

    def append_category(self, category):
        """Append one category record to the editor table."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        enabled = QCheckBox()
        enabled.setChecked(category.enabled)
        enabled.setStyleSheet("margin-left: 15px")
        enabled.stateChanged.connect(self.mark_dirty)
        self.table.setCellWidget(row, 0, enabled)
        self.table.setItem(row, 1, QTableWidgetItem(str(category.id)))
        self.table.setItem(row, 2, QTableWidgetItem(category.name))
        self.table.setItem(row, 3, QTableWidgetItem(category.supercategory))
        self.table.setItem(row, 4, QTableWidgetItem(category.description))

    def mark_dirty(self, *_):
        """Mark the current editor contents as modified."""
        if not self.loading:
            self.dirty = True
            self.update_state()

    def update_state(self):
        """Refresh labels and actions for the selected configuration state."""
        self.config_title.setText(
            self.display_config_name(self.config_id, self.config_name)
        )
        hint_key = "category.hint.draft" if self.is_draft else "category.hint.readonly"
        self.config_hint.setText(self.t(hint_key))
        self.uuid_label.setText(self.config_id or "")
        self.created_at_label.setText(
            self.created_at or self.t("category.not_created")
        )
        self.parent_version_label.setText(self.parent_version_display())
        self.save_button.setText(self.t("common.save"))
        self.save_button.setEnabled(self.is_draft)
        self.copy_button.setEnabled(not self.is_draft)
        self.add_entry_button.setEnabled(self.is_draft)
        self.delete_entry_button.setEnabled(self.is_draft)
        self.table.setEditTriggers(
            QAbstractItemView.AllEditTriggers
            if self.is_draft
            else QAbstractItemView.NoEditTriggers
        )
        for row in range(self.table.rowCount()):
            enabled = self.table.cellWidget(row, 0)
            if enabled is not None:
                enabled.setEnabled(self.is_draft)

    def _text(self, row, column):
        """Return trimmed text from an editor cell."""
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    def parent_version_display(self):
        """Return the parent configuration UUID and filename for display."""
        parent_id = self.parent_version_uuid
        if parent_id is None:
            return self.t("category.parent_version_none")
        try:
            filename = self.manager.config_filename(parent_id)
        except CategoryConfigError:
            return self.t("category.parent_version_missing", uuid=parent_id)
        return f"{parent_id} · {filename}"

    def categories(self):
        """Build validated category objects from the editor rows."""
        categories = []
        for row in range(self.table.rowCount()):
            enabled_widget = self.table.cellWidget(row, 0)
            try:
                category = Category(
                    id=int(self._text(row, 1)),
                    name=self._text(row, 2),
                    supercategory=self._text(row, 3),
                    description=self._text(row, 4),
                    enabled=enabled_widget.isChecked(),
                )
            except (AttributeError, ValueError) as error:
                raise CategoryConfigError(
                    self.t("category.invalid_row", row=row + 1)
                ) from error
            categories.append(category)
        CategoryStore.validate(categories)
        return categories

    def commit_table_editor(self):
        """Commit the active table editor before reading cell values."""
        editor = QApplication.focusWidget()
        if editor is None or not self.table.isAncestorOf(editor):
            return
        self.table.commitData(editor)
        self.table.closeEditor(editor, QAbstractItemDelegate.SubmitModelCache)

    def ask_name(self, title, initial=""):
        """Ask for a configuration name and normalize whitespace."""
        name, accepted = QInputDialog.getText(
            self, title, self.t("category.name_prompt"), text=initial
        )
        return name.strip() if accepted else None

    def new_config(self):
        """Start an empty named configuration draft."""
        if not self.resolve_unsaved_changes():
            return
        name = self.ask_name(self.t("category.new_title"))
        if not name:
            return
        if self.is_draft and self.draft_saved:
            self.manager.freeze(self.config_id)
        self.config_id = self.manager.new_uuid()
        self.config_name = name
        self.created_at = ""
        self.parent_version_uuid = None
        self.is_draft = True
        self.draft_saved = False
        self.populate([])
        self.dirty = True
        self.config_list.blockSignals(True)
        self.config_list.clearSelection()
        self.config_list.blockSignals(False)
        self.update_state()

    def copy_config(self):
        """Copy the visible editor contents into a new named draft."""
        if self.is_draft:
            return
        try:
            categories = self.categories()
        except CategoryConfigError as error:
            QMessageBox.critical(self, self.t("category.error"), str(error))
            return
        name = self.ask_name(
            self.t("category.copy_title"),
            self.t(
                "category.copy_suffix",
                name=self.display_config_name(self.config_id, self.config_name),
            ),
        )
        if not name:
            return
        config_id = self.manager.new_uuid()
        try:
            self.manager.create(
                name,
                config_id,
                categories,
                parent_version_uuid=self.config_id,
            )
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, self.t("category.copy_failed"), str(error))
            return
        self.config_id = config_id
        self.config_name = name
        data = self.manager.load_data(config_id)
        self.created_at = data.created_at
        self.parent_version_uuid = data.parent_version_uuid
        self.is_draft = True
        self.draft_saved = True
        self.populate(categories)
        self.dirty = False
        self.refresh_config_list(self.config_id)
        self.update_state()

    def add_empty_row(self):
        """Add a new editable category row with a unique identifier."""
        identifiers = []
        for row in range(self.table.rowCount()):
            try:
                identifiers.append(int(self._text(row, 1)))
            except ValueError:
                pass
        self.append_category(Category(max(identifiers, default=0) + 1, "", ""))
        self.mark_dirty()
        self.table.scrollToBottom()
        self.table.setCurrentCell(self.table.rowCount() - 1, 2)
        self.table.editItem(self.table.currentItem())

    def delete_selected_rows(self):
        """Delete every selected category row after confirmation."""
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        answer = QMessageBox.question(
            self,
            self.t("category.delete_entries_title"),
            self.t("category.delete_entries_confirm", count=len(rows)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            for row in rows:
                self.table.removeRow(row)
            self.mark_dirty()

    def save_current(self):
        """Create or update the draft owned by this editor session."""
        if not self.is_draft:
            return False
        self.commit_table_editor()
        try:
            categories = self.categories()
            if self.draft_saved:
                self.manager.save_draft(self.config_id, categories)
            else:
                self.manager.create(self.config_name, self.config_id, categories)
                data = self.manager.load_data(self.config_id)
                self.created_at = data.created_at
                self.parent_version_uuid = data.parent_version_uuid
                self.draft_saved = True
            self.dirty = False
            self.refresh_config_list(self.config_id)
            self.update_state()
            if self.active_config_id == self.config_id:
                self.configurationApplied.emit(self.config_id)
            return True
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, self.t("category.save_failed"), str(error))
            return False

    def resolve_unsaved_changes(self):
        """Ask whether to save, discard, or keep editing modified contents."""
        self.commit_table_editor()
        if not self.dirty:
            return True
        answer = QMessageBox.warning(
            self,
            self.t("category.unsaved_title"),
            self.t("category.unsaved_confirm"),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self.save_current()
        if answer == QMessageBox.Discard:
            return True
        return False

    def apply_current(self):
        """Save pending edits, apply the configuration, and keep it for startup."""
        self.commit_table_editor()
        if self.dirty and not self.save_current():
            return
        if self.config_id is None:
            return
        try:
            if self.apply_validator is not None and not self.apply_validator(self.config_id):
                return
            self.manager.set_default(self.config_id)
            self.active_config_id = self.config_id
            self.applied_config_id = self.config_id
            self.refresh_config_list(self.config_id)
            self.configurationApplied.emit(self.config_id)
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, self.t("category.apply_failed"), str(error))

    def reject(self):
        """Close only after resolving pending edits."""
        if self.resolve_unsaved_changes():
            if self.is_draft and self.draft_saved:
                self.manager.freeze(self.config_id)
            super().reject()

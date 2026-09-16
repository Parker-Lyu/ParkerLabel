from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
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
from .models import Category


class CategoryConfigDialog(QDialog):
    COLUMNS = ("启用", "ID", "名称", "上级类别", "描述")

    def __init__(self, manager, active_config_id, parent=None):
        """Create a manager for built-in and named user category configurations."""
        super().__init__(parent)
        self.manager = manager
        self.active_config_id = active_config_id
        self.applied_config_id = None
        self.config_id = None
        self.config_name = ""
        self.dirty = False
        self.loading = False
        self.setWindowTitle("类别配置")
        self.resize(1180, 720)
        self.build_ui()
        self.refresh_config_list(active_config_id)
        self.load_config(active_config_id)

    def build_ui(self):
        """Build configuration actions, list, category table, and dialog actions."""
        new_button = QPushButton("新建空白")
        copy_button = QPushButton("复制所选")
        self.rename_button = QPushButton("重命名")
        self.default_button = QPushButton("设为启动默认")
        self.delete_config_button = QPushButton("删除配置")
        new_button.clicked.connect(self.new_config)
        copy_button.clicked.connect(self.copy_config)
        self.rename_button.clicked.connect(self.rename_config)
        self.default_button.clicked.connect(self.set_default_config)
        self.delete_config_button.clicked.connect(self.delete_config)
        toolbar = QHBoxLayout()
        for button in (
            new_button,
            copy_button,
            self.rename_button,
            self.default_button,
            self.delete_config_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch(1)

        self.config_list = QListWidget()
        self.config_list.setFixedWidth(230)
        self.config_list.currentItemChanged.connect(self.change_config)

        self.config_title = QLabel()
        self.config_hint = QLabel()
        self.config_hint.setStyleSheet("color: palette(mid)")
        heading = QHBoxLayout()
        heading.addWidget(self.config_title)
        heading.addSpacing(12)
        heading.addWidget(self.config_hint)
        heading.addStretch(1)

        self.table = QTableWidget(0, len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 58)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 170)
        self.table.setColumnWidth(3, 160)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(self.mark_dirty)

        add_button = QPushButton("新增条目")
        delete_button = QPushButton("删除条目")
        add_button.clicked.connect(self.add_empty_row)
        delete_button.clicked.connect(self.delete_selected_rows)
        row_actions = QHBoxLayout()
        row_actions.addWidget(add_button)
        row_actions.addWidget(delete_button)
        row_actions.addStretch(1)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addLayout(heading)
        editor_layout.addLayout(row_actions)
        editor_layout.addWidget(self.table)

        content = QHBoxLayout()
        content.addWidget(self.config_list)
        content.addWidget(editor, 1)

        buttons = QDialogButtonBox()
        self.save_button = buttons.addButton("保存", QDialogButtonBox.ActionRole)
        self.apply_button = buttons.addButton("应用到当前会话", QDialogButtonBox.AcceptRole)
        close_button = buttons.addButton("关闭", QDialogButtonBox.RejectRole)
        self.save_button.clicked.connect(self.save_current)
        self.apply_button.clicked.connect(self.apply_current)
        close_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addLayout(content, 1)
        layout.addWidget(buttons)

    def refresh_config_list(self, selected_id=None):
        """Reload configuration names and status markers."""
        default_id = self.manager.default_config_id()
        self.config_list.blockSignals(True)
        self.config_list.clear()
        selected_item = None
        for config in self.manager.configurations():
            labels = []
            if config.builtin:
                labels.append("内置")
            if config.id == default_id:
                labels.append("启动默认")
            if config.id == self.active_config_id:
                labels.append("当前使用")
            suffix = f"\n{' · '.join(labels)}" if labels else ""
            item = QListWidgetItem(f"{config.name}{suffix}")
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
        categories = self.manager.load(config_id)
        self.config_id = config.id
        self.config_name = config.name
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
        try:
            self.load_config(config_id)
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, "类别配置错误", str(error))
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
        builtin = self.config_id == CategoryConfigManager.BUILTIN_ID
        self.config_title.setText(self.config_name)
        self.config_hint.setText(
            "内置配置不可覆盖，保存时将创建副本" if builtin else "用户配置"
        )
        self.save_button.setText("另存为…" if builtin or self.config_id is None else "保存")
        saved_user = self.config_id not in (None, CategoryConfigManager.BUILTIN_ID)
        self.rename_button.setEnabled(saved_user)
        self.delete_config_button.setEnabled(saved_user)
        self.default_button.setEnabled(self.config_id is not None)

    def _text(self, row, column):
        """Return trimmed text from an editor cell."""
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

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
                raise CategoryConfigError(f"第 {row + 1} 行包含无效值") from error
            categories.append(category)
        CategoryStore.validate(categories)
        return categories

    def ask_name(self, title, initial=""):
        """Ask for a configuration name and normalize whitespace."""
        name, accepted = QInputDialog.getText(self, title, "配置名称：", text=initial)
        return name.strip() if accepted else None

    def new_config(self):
        """Start an empty named configuration draft."""
        if not self.resolve_unsaved_changes():
            return
        name = self.ask_name("新建类别配置")
        if not name:
            return
        self.config_id = None
        self.config_name = name
        self.populate([])
        self.dirty = True
        self.config_list.blockSignals(True)
        self.config_list.clearSelection()
        self.config_list.blockSignals(False)
        self.update_state()

    def copy_config(self):
        """Copy the visible editor contents into a new named draft."""
        try:
            categories = self.categories()
        except CategoryConfigError as error:
            QMessageBox.critical(self, "类别配置错误", str(error))
            return
        name = self.ask_name("复制类别配置", f"{self.config_name} 副本")
        if not name:
            return
        self.config_id = None
        self.config_name = name
        self.populate(categories)
        self.dirty = True
        self.config_list.blockSignals(True)
        self.config_list.clearSelection()
        self.config_list.blockSignals(False)
        self.update_state()

    def rename_config(self):
        """Rename the selected user configuration."""
        if self.config_id in (None, CategoryConfigManager.BUILTIN_ID):
            return
        name = self.ask_name("重命名类别配置", self.config_name)
        if not name or name == self.config_name:
            return
        try:
            self.manager.rename(self.config_id, name)
            self.config_name = name
            self.refresh_config_list(self.config_id)
            self.update_state()
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, "重命名失败", str(error))

    def set_default_config(self):
        """Set the selected saved configuration as the startup default."""
        if self.config_id is None:
            return
        if self.dirty and not self.save_current():
            return
        try:
            self.manager.set_default(self.config_id)
            self.refresh_config_list(self.config_id)
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, "设置默认配置失败", str(error))

    def delete_config(self):
        """Delete the selected user configuration after confirmation."""
        if self.config_id in (None, CategoryConfigManager.BUILTIN_ID):
            return
        answer = QMessageBox.question(
            self,
            "删除类别配置",
            f"确认删除“{self.config_name}”？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            deleted_id = self.config_id
            self.manager.delete(deleted_id)
            if self.active_config_id == deleted_id:
                self.active_config_id = CategoryConfigManager.BUILTIN_ID
            self.refresh_config_list(CategoryConfigManager.BUILTIN_ID)
            self.load_config(CategoryConfigManager.BUILTIN_ID)
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, "删除配置失败", str(error))

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
            "删除类别条目",
            f"确认删除选中的 {len(rows)} 个类别条目？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            for row in rows:
                self.table.removeRow(row)
            self.mark_dirty()

    def save_current(self):
        """Save a user configuration or create a copy of the built-in set."""
        try:
            categories = self.categories()
            if self.config_id in (None, CategoryConfigManager.BUILTIN_ID):
                initial = self.config_name if self.config_id is None else ""
                name = self.ask_name("另存类别配置", initial)
                if not name:
                    return False
                self.config_id = self.manager.create(name, categories)
                self.config_name = name
            else:
                self.manager.save(self.config_id, categories)
            self.dirty = False
            self.refresh_config_list(self.config_id)
            self.update_state()
            return True
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, "保存类别配置失败", str(error))
            return False

    def resolve_unsaved_changes(self):
        """Ask whether to save, discard, or keep editing modified contents."""
        if not self.dirty:
            return True
        answer = QMessageBox.warning(
            self,
            "未保存的类别配置",
            "当前类别配置已修改，是否保存？",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self.save_current()
        if answer == QMessageBox.Discard:
            return True
        return False

    def apply_current(self):
        """Save pending edits and apply the selected configuration to the session."""
        if self.dirty and not self.save_current():
            return
        if self.config_id is None:
            return
        self.applied_config_id = self.config_id
        self.accept()

    def reject(self):
        """Close only after resolving pending edits."""
        if self.resolve_unsaved_changes():
            super().reject()

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .category_store import CategoryConfigError
from .models import Category


class CategoryConfigDialog(QDialog):
    COLUMNS = ("启用", "ID", "名称", "上级类别", "描述")

    def __init__(self, store, parent=None):
        """Create an editable dialog for the local category configuration."""
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("类别配置")
        self.resize(1050, 680)
        self.table = QTableWidget(0, len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 52)
        self.table.setColumnWidth(1, 64)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 140)
        self.table.horizontalHeader().setStretchLastSection(True)
        add_button = QPushButton("新增")
        delete_button = QPushButton("删除选中")
        add_button.clicked.connect(self.add_empty_row)
        delete_button.clicked.connect(self.delete_selected_rows)
        controls = QHBoxLayout()
        controls.addWidget(add_button)
        controls.addWidget(delete_button)
        controls.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.table)
        layout.addWidget(buttons)
        self.populate(self.store.load())

    def populate(self, categories):
        """Populate the table with category records."""
        self.table.setRowCount(0)
        for category in categories:
            self.append_category(category)

    def append_category(self, category):
        """Append one category record to the editor table."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        enabled = QCheckBox()
        enabled.setChecked(category.enabled)
        enabled.setStyleSheet("margin-left: 14px")
        self.table.setCellWidget(row, 0, enabled)
        self.table.setItem(row, 1, QTableWidgetItem(str(category.id)))
        self.table.setItem(row, 2, QTableWidgetItem(category.name))
        self.table.setItem(row, 3, QTableWidgetItem(category.supercategory))
        self.table.setItem(row, 4, QTableWidgetItem(category.description))

    def add_empty_row(self):
        """Add a new editable category row with a unique identifier."""
        identifiers = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is not None:
                try:
                    identifiers.append(int(item.text()))
                except ValueError:
                    pass
        next_id = max(identifiers, default=0) + 1
        self.append_category(Category(next_id, "", ""))
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
            "删除类别",
            f"确认删除选中的 {len(rows)} 个类别？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            for row in rows:
                self.table.removeRow(row)

    def _text(self, row, column):
        """Return trimmed text from an editor cell."""
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    def categories(self):
        """Build validated category objects from the editor rows."""
        categories = []
        for row in range(self.table.rowCount()):
            enabled = self.table.cellWidget(row, 0).isChecked()
            try:
                category = Category(
                    id=int(self._text(row, 1)),
                    name=self._text(row, 2),
                    supercategory=self._text(row, 3),
                    description=self._text(row, 4),
                    enabled=enabled,
                )
            except ValueError as error:
                raise CategoryConfigError(f"第 {row + 1} 行包含无效数字") from error
            categories.append(category)
        self.store.validate(categories)
        return categories

    def save_and_accept(self):
        """Persist the edited categories and close the dialog."""
        try:
            self.store.save(self.categories())
        except (CategoryConfigError, OSError) as error:
            QMessageBox.critical(self, "类别配置错误", str(error))
            return
        self.accept()

import random
import traceback
from pathlib import Path

import cv2
import numpy as np
from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .annotation_io import AnnotationRepository
from .canvas import AnnotationCanvas
from .category_dialog import CategoryConfigDialog
from .category_store import CategoryStore
from .image_utils import color_id_to_rgb, id_mask_to_rgb, qimage_from_rgb
from .inference import SegmentationEngine


class VisibilityHeader(QHeaderView):
    visibilityChanged = pyqtSignal(bool)

    def __init__(self, display_column, parent=None):
        """Create a header with a checkbox for global visibility."""
        super().__init__(Qt.Horizontal, parent)
        self.display_column = display_column
        self.checkbox = QCheckBox("显示", self)
        self.checkbox.setTristate(True)
        self.checkbox.stateChanged.connect(self.emit_visibility)
        self.sectionResized.connect(self.update_checkbox_geometry)
        self.sectionMoved.connect(self.update_checkbox_geometry)

    def emit_visibility(self, state):
        """Emit global visibility changes for checked and unchecked states."""
        if state != Qt.PartiallyChecked:
            self.visibilityChanged.emit(state == Qt.Checked)

    def set_visibility_state(self, state, enabled):
        """Update the header checkbox without emitting a user action."""
        self.checkbox.blockSignals(True)
        self.checkbox.setCheckState(state)
        self.checkbox.setEnabled(enabled)
        self.checkbox.blockSignals(False)

    def update_checkbox_geometry(self):
        """Center the global visibility checkbox in its header section."""
        position = self.sectionViewportPosition(self.display_column)
        width = self.sectionSize(self.display_column)
        hint = self.checkbox.sizeHint()
        self.checkbox.setGeometry(
            position + max(0, (width - hint.width()) // 2),
            max(0, (self.height() - hint.height()) // 2),
            min(width, hint.width()),
            hint.height(),
        )

    def resizeEvent(self, event):
        """Keep the global visibility checkbox aligned after resizing."""
        super().resizeEvent(event)
        self.update_checkbox_geometry()


class MainWindow(QWidget):
    COL_ID = 0
    COL_EDIT = 1
    COL_SHOW = 2
    COL_CATEGORY = 3
    COL_COLOR = 4
    COL_DELETE = 5

    def __init__(self):
        """Initialize application services, state, and interface."""
        super().__init__()
        root = Path(__file__).resolve().parent.parent
        self.category_store = CategoryStore(root / "config" / "categories.json")
        self.repository = AnnotationRepository(target_size=1024)
        self.engine = SegmentationEngine(
            root / "pretrain" / "encoder.onnx",
            root / "pretrain" / "H" / "decoder.onnx",
            target_size=1024,
        )
        self.categories = []
        self.categories_by_name = {}
        self.document = None
        self.current_index = None
        self.edit_mask = None
        self.edit_dirty = False
        self.metadata_dirty = False
        self.metadata_snapshot = None
        self.prompt_points = []
        self.prompt_labels = []
        self.previous_logits = None
        self.mode = "query"
        self.view_mode = "overlay"
        self.zoom_factor = 1.0
        self.minimum_zoom = 0.1
        self.maximum_zoom = 10.0
        self.zoom_step = 1.15
        self.base_canvas_size = (1, 1)
        self.canvas_size = (1, 1)
        self.panning = False
        self.pan_origin = None
        self.painting = None
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.load_categories()
        self.build_ui()
        self.reset_document_view()
        self.log("初始化完成，请打开图片")

    def load_categories(self):
        """Load enabled category records from the local JSON configuration."""
        self.categories = self.category_store.enabled()
        self.categories_by_name = {category.name: category for category in self.categories}

    def build_ui(self):
        """Build the annotation workspace and connect user actions."""
        self.setWindowTitle("Parker Label")
        screen = QApplication.primaryScreen().availableSize()
        self.resize(max(1100, screen.width() - 80), max(720, screen.height() - 80))
        self.canvas = AnnotationCanvas(self)
        self.canvas.setText("请打开图片")
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        controls = QVBoxLayout()
        self.primary_controls = self.build_primary_controls()
        self.tool_controls = self.build_tool_controls()
        controls.addLayout(self.primary_controls)
        controls.addLayout(self.tool_controls)
        self.table = self.build_segment_table()
        controls.addWidget(self.table, 1)
        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(170)
        controls.addWidget(self.log_area)
        self.control_panel = QWidget(self)
        self.control_panel.setLayout(controls)
        layout = QHBoxLayout(self)
        layout.addWidget(self.scroll_area, 1)
        layout.addWidget(self.control_panel)
        self.resize_segment_table_columns()

    def build_primary_controls(self):
        """Create file, category, and save actions."""
        layout = QGridLayout()
        open_button = QPushButton("打开图片")
        category_button = QPushButton("类别配置")
        save_button = QPushButton("保存到磁盘")
        save_button.setShortcut("Ctrl+S")
        open_button.clicked.connect(self.choose_image)
        category_button.clicked.connect(self.configure_categories)
        save_button.clicked.connect(self.save_document)
        buttons = (open_button, category_button, save_button)
        button_width = max(button.sizeHint().width() for button in buttons)
        for button in buttons:
            button.setFixedWidth(button_width)
        layout.addWidget(open_button, 0, 0)
        layout.addWidget(category_button, 1, 0)
        layout.addWidget(save_button, 1, 1)
        layout.setAlignment(Qt.AlignLeft)
        return layout

    def build_tool_controls(self):
        """Create drawing, viewing, morphology, and brush controls."""
        outer = QVBoxLayout()

        edit_group = QGroupBox("目标编辑")
        edit_layout = QVBoxLayout(edit_group)
        self.undo_button = QPushButton("撤销")
        self.redo_button = QPushButton("重做")
        self.add_button = QPushButton("增加目标")
        self.commit_button = QPushButton("提交当前目标")
        self.add_button.setShortcut("A")
        self.add_button.clicked.connect(self.add_segment)
        self.commit_button.clicked.connect(self.commit_current_segment)
        edit_layout.addWidget(self.undo_button)
        edit_layout.addWidget(self.redo_button)
        edit_layout.addWidget(self.add_button)
        edit_layout.addWidget(self.commit_button)

        view_group = QGroupBox("显示模式")
        view_layout = QVBoxLayout(view_group)
        self.view_group = QButtonGroup(self)
        views = (("原图", "image"), ("Mask", "mask"), ("叠加", "overlay"))
        for label, value in views:
            button = QRadioButton(label)
            button.setProperty("value", value)
            self.view_group.addButton(button)
            view_layout.addWidget(button)
            if value == self.view_mode:
                button.setChecked(True)
        self.view_group.buttonClicked.connect(self.change_view)

        interaction_group = QGroupBox("交互模式")
        interaction_layout = QVBoxLayout(interaction_group)
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        modes = (("智能", "smart"), ("手动", "brush"), ("查询", "query"))
        for label, value in modes:
            button = QRadioButton(label)
            button.setProperty("value", value)
            self.mode_group.addButton(button)
            mode_layout.addWidget(button)
            if value == self.mode:
                button.setChecked(True)
        self.mode_group.buttonClicked.connect(self.change_mode)
        mode_layout.addStretch(1)

        brush_layout = QHBoxLayout()
        self.brush_label = QLabel("画笔尺寸：5")
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 50)
        self.brush_slider.setValue(5)
        self.brush_slider.valueChanged.connect(
            lambda value: self.brush_label.setText(f"画笔尺寸：{value}")
        )
        brush_layout.addWidget(self.brush_label)
        brush_layout.addWidget(self.brush_slider, 1)

        morphology_layout = QHBoxLayout()
        self.erode_button = QPushButton("腐蚀")
        self.dilate_button = QPushButton("膨胀")
        self.erode_button.clicked.connect(self.erode_edit_mask)
        self.dilate_button.clicked.connect(self.dilate_edit_mask)
        morphology_layout.addWidget(self.erode_button)
        morphology_layout.addWidget(self.dilate_button)

        interaction_layout.addLayout(mode_layout)
        interaction_layout.addLayout(brush_layout)
        interaction_layout.addLayout(morphology_layout)
        self.manual_controls = (
            self.brush_label,
            self.brush_slider,
            self.erode_button,
            self.dilate_button,
        )

        group_style = (
            "QGroupBox { border: 1px solid #8c8c8c; border-radius: 3px; "
            "margin-top: 8px; padding-top: 6px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
        )
        for group in (edit_group, view_group, interaction_group):
            group.setStyleSheet(group_style)
        lower_row = QHBoxLayout()
        lower_row.addWidget(edit_group, 0, Qt.AlignLeft)
        lower_row.addWidget(view_group, 0, Qt.AlignLeft)
        lower_row.addStretch(1)
        outer.addWidget(interaction_group, 0, Qt.AlignLeft)
        outer.addLayout(lower_row)
        self.update_tool_controls()
        return outer

    def build_segment_table(self):
        """Create the segment table used to edit document-backed records."""
        table = QTableWidget(0, 6, self)
        header = VisibilityHeader(self.COL_SHOW, table)
        table.setHorizontalHeader(header)
        table.setHorizontalHeaderLabels(["ID", "编辑", "", "类别", "颜色", "删除"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setMinimumSectionSize(44)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        header.visibilityChanged.connect(self.set_all_segments_visible)
        table.cellClicked.connect(self.handle_segment_cell_click)
        header.update_checkbox_geometry()
        return table

    def reset_document_view(self):
        """Reset table and canvas state when no document is active."""
        self.current_index = None
        self.edit_mask = None
        self.edit_dirty = False
        self.metadata_dirty = False
        self.metadata_snapshot = None
        self.prompt_points = []
        self.prompt_labels = []
        self.previous_logits = None
        self.table.setRowCount(0)
        self.canvas.setText("请打开图片")
        self.canvas.setFixedSize(640, 480)

    def choose_image(self):
        """Open a file picker and load the selected image."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开图片",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp)",
        )
        if path:
            self.open_image(path)

    def open_image(self, path):
        """Open an image and its existing annotation artifacts."""
        suffix = Path(path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".bmp"}:
            self.show_warning("无法打开图片", "仅支持 jpg、jpeg、png 和 bmp 图片")
            return
        if not self.confirm_document_transition():
            return
        try:
            self.document = self.repository.open(Path(path))
            self.current_index = None
            self.clear_edit_state()
            self.zoom_factor = 1.0
            self.calculate_base_canvas_size()
            self.refresh_table()
            self.refresh_canvas()
            self.log(f"已打开图片：{self.document.image_path.name}")
            if self.document.embedding is None:
                self.ensure_embedding()
            else:
                self.log("已读取现有图片特征")
        except Exception as error:
            self.log_exception("打开图片失败", error)

    def confirm_document_transition(self):
        """Ask how to handle unsaved work before replacing the document."""
        if self.document is None or not (self.document.dirty or self.has_pending_target_edit()):
            return True
        answer = QMessageBox.question(
            self,
            "标注尚未存盘",
            "当前图片有标注修改尚未存盘，是否存盘？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Yes:
            return self.save_document()
        return True

    def calculate_base_canvas_size(self):
        """Fit the active image inside the initial canvas area."""
        if self.document is None:
            return
        image_height, image_width = self.document.image_rgb.shape[:2]
        viewport_width = max(320, int(self.width() * 0.56))
        viewport_height = max(320, self.height() - 80)
        scale = min(viewport_width / image_width, viewport_height / image_height)
        scale = min(scale, 1.0)
        self.base_canvas_size = (
            max(1, int(round(image_width * scale))),
            max(1, int(round(image_height * scale))),
        )
        self.apply_canvas_size()

    def apply_canvas_size(self):
        """Apply the current zoom factor to the canvas dimensions."""
        width = max(1, int(round(self.base_canvas_size[0] * self.zoom_factor)))
        height = max(1, int(round(self.base_canvas_size[1] * self.zoom_factor)))
        self.canvas_size = (width, height)
        self.canvas.setFixedSize(width, height)

    def refresh_table(self):
        """Rebuild table widgets from the annotation document."""
        self.table.setRowCount(0)
        if self.document is None:
            self.update_visibility_header()
            self.resize_segment_table_columns()
            return
        for index, segment in enumerate(self.document.segments):
            self.table.insertRow(index)
            identifier = QLabel(str(index + 1))
            identifier.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(index, self.COL_ID, identifier)
            edit = QRadioButton()
            edit.setChecked(index == self.current_index)
            edit.clicked.connect(lambda checked=False, row=index: self.select_segment(row))
            self.table.setCellWidget(index, self.COL_EDIT, self.create_centered_control(edit))
            visible = QCheckBox()
            visible.setChecked(segment.visible)
            visible.toggled.connect(lambda checked, row=index: self.set_segment_visibility(row, checked))
            self.table.setCellWidget(index, self.COL_SHOW, self.create_centered_control(visible))
            category = self.create_category_combo(segment.category_name)
            category.setEnabled(index == self.current_index)
            category.currentTextChanged.connect(lambda name, row=index: self.set_segment_category(row, name))
            self.table.setCellWidget(index, self.COL_CATEGORY, category)
            color = QPushButton(self.color_button_text(segment.color_id))
            color.setStyleSheet(self.color_button_style(segment.color_id))
            color.setEnabled(index == self.current_index)
            color.clicked.connect(lambda checked=False, row=index: self.assign_random_color(row))
            self.table.setCellWidget(index, self.COL_COLOR, color)
            delete = QPushButton("删除")
            delete.clicked.connect(lambda checked=False, row=index: self.delete_segment(row))
            self.table.setCellWidget(index, self.COL_DELETE, delete)
        if self.current_index is not None and self.current_index < self.table.rowCount():
            self.table.selectRow(self.current_index)
        self.update_visibility_header()
        self.resize_segment_table_columns()

    def resize_segment_table_columns(self):
        """Size table columns and the control panel from their contents."""
        self.table.resizeColumnsToContents()
        category_probe = QComboBox()
        selected_categories = (
            [segment.category_name for segment in self.document.segments]
            if self.document is not None
            else []
        )
        category_probe.addItems(selected_categories or ["类别"])
        self.table.setColumnWidth(self.COL_CATEGORY, category_probe.sizeHint().width())
        self.table.horizontalHeader().update_checkbox_geometry()
        if not hasattr(self, "control_panel"):
            return
        table_width = self.table.frameWidth() * 2
        table_width += sum(self.table.columnWidth(column) for column in range(self.table.columnCount()))
        table_width += self.table.verticalScrollBar().sizeHint().width()
        content_width = max(
            table_width,
            self.primary_controls.sizeHint().width(),
            self.tool_controls.sizeHint().width(),
            self.log_area.minimumSizeHint().width(),
        )
        margins = self.control_panel.layout().contentsMargins()
        self.control_panel.setFixedWidth(content_width + margins.left() + margins.right())

    def create_centered_control(self, control):
        """Place a compact control in the center of a table cell."""
        container = QWidget(self.table)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(control)
        layout.addStretch(1)
        return container

    def handle_segment_cell_click(self, row, column):
        """Handle full-cell edit selection and visibility toggling."""
        if self.document is None or row >= len(self.document.segments):
            return
        if column == self.COL_EDIT:
            self.select_segment(row)
        elif column == self.COL_SHOW:
            self.set_segment_visibility(row, not self.document.segments[row].visible)

    def update_visibility_header(self):
        """Synchronize the header checkbox with segment visibility."""
        header = self.table.horizontalHeader()
        if self.document is None or not self.document.segments:
            header.set_visibility_state(Qt.Unchecked, False)
            return
        states = [segment.visible for segment in self.document.segments]
        if all(states):
            state = Qt.Checked
        elif any(states):
            state = Qt.PartiallyChecked
        else:
            state = Qt.Unchecked
        header.set_visibility_state(state, True)

    def set_all_segments_visible(self, visible):
        """Set the visibility of every segment from the header checkbox."""
        if self.document is None:
            return
        for segment in self.document.segments:
            segment.visible = visible
        self.refresh_table()
        self.refresh_canvas()

    def create_category_combo(self, current_name):
        """Create a category selector that preserves unavailable current values."""
        combo = QComboBox(self)
        combo.setEditable(True)
        names = [category.name for category in self.categories]
        if current_name and current_name not in names:
            names.insert(0, current_name)
        combo.addItems(names)
        combo.setCurrentText(current_name)
        for index, name in enumerate(names):
            category = self.categories_by_name.get(name)
            if category is not None:
                description = category.description or "无描述"
                combo.setItemData(index, f"{category.supercategory}\n{description}", Qt.ToolTipRole)
        return combo

    def configure_categories(self):
        """Open the local JSON category editor and refresh selectors after saving."""
        try:
            dialog = CategoryConfigDialog(self.category_store, self)
            if dialog.exec_():
                self.load_categories()
                self.refresh_table()
                self.log(f"类别配置已更新，共启用 {len(self.categories)} 个类别")
        except Exception as error:
            self.log_exception("打开类别配置失败", error)

    def add_segment(self):
        """Add an empty segment using the first enabled category."""
        if self.document is None:
            self.show_warning("无法增加目标", "请先打开图片")
            return
        if not self.categories:
            self.show_warning("无法增加目标", "类别配置中没有启用的类别")
            return
        if self.current_index is not None and not self.resolve_pending_edit():
            return
        if self.current_index is not None:
            current_mask = self.document.segments[self.current_index].mask
            if current_mask is None or not np.any(current_mask):
                self.show_warning("无法增加目标", "当前目标尚未标注，不能继续增加目标")
                return
        category = self.categories[0]
        color_id = self.generate_color_id()
        self.document.add_segment(category, color_id)
        self.current_index = len(self.document.segments) - 1
        self.mode = "smart"
        self.set_checked_button(self.mode_group, "smart")
        self.clear_edit_state()
        self.refresh_table()
        self.update_tool_controls()
        self.refresh_canvas()

    def generate_color_id(self):
        """Generate a unique nonzero packed RGB identifier."""
        used = self.document.used_color_ids() if self.document is not None else set()
        while True:
            red, green, blue = (random.randrange(256) for _ in range(3))
            color_id = red + green * 256 + blue * 65536
            if color_id and color_id not in used:
                return color_id

    def select_segment(self, index):
        """Select a segment after resolving any pending mask edit."""
        if index == self.current_index:
            return
        if not self.resolve_pending_edit():
            self.refresh_table()
            return
        self.current_index = index
        self.clear_edit_state()
        self.refresh_table()
        self.refresh_canvas()

    def resolve_pending_edit(self):
        """Ask whether to commit or discard pending target changes."""
        if not self.has_pending_target_edit():
            return True
        answer = QMessageBox.question(
            self,
            "编辑尚未提交",
            "当前目标的编辑尚未提交，是否提交？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Cancel:
            return False
        if answer == QMessageBox.Yes:
            return self.commit_current_segment()
        self.discard_edit()
        return True

    def has_pending_target_edit(self):
        """Return whether the current target has uncommitted changes."""
        return self.edit_dirty or self.metadata_dirty

    def begin_metadata_edit(self, index):
        """Capture current target metadata before its first pending change."""
        if (
            self.metadata_snapshot is not None
            or self.document is None
            or index != self.current_index
        ):
            return
        segment = self.document.segments[index]
        self.metadata_snapshot = (
            segment.category_id,
            segment.category_name,
            segment.color_id,
            self.document.dirty,
        )

    def update_metadata_dirty(self, index):
        """Update pending metadata state after a category or color change."""
        if self.metadata_snapshot is None or self.document is None or index != self.current_index:
            return
        segment = self.document.segments[index]
        original = self.metadata_snapshot[:3]
        current = (segment.category_id, segment.category_name, segment.color_id)
        self.metadata_dirty = current != original
        if not self.metadata_dirty:
            self.document.dirty = self.metadata_snapshot[3]
            self.metadata_snapshot = None

    def set_segment_visibility(self, index, visible):
        """Update segment visibility without changing saved mask data."""
        if self.document is None or index >= len(self.document.segments):
            return
        self.document.segments[index].visible = visible
        container = self.table.cellWidget(index, self.COL_SHOW)
        checkbox = container.findChild(QCheckBox) if container is not None else None
        if checkbox is not None and checkbox.isChecked() != visible:
            checkbox.blockSignals(True)
            checkbox.setChecked(visible)
            checkbox.blockSignals(False)
        self.update_visibility_header()
        self.refresh_canvas()

    def set_segment_category(self, index, name):
        """Assign a selected configured category to a segment."""
        if self.document is None or index >= len(self.document.segments):
            return
        category = self.categories_by_name.get(name)
        if category is None:
            return
        segment = self.document.segments[index]
        if segment.category_id == category.id and segment.category_name == category.name:
            return
        self.begin_metadata_edit(index)
        self.document.change_segment_category(index, category)
        self.update_metadata_dirty(index)
        self.resize_segment_table_columns()
        self.refresh_canvas()

    def assign_random_color(self, index):
        """Assign a new random display color to the current segment."""
        if self.document is None or index != self.current_index:
            return
        self.begin_metadata_edit(index)
        self.document.change_segment_color(index, self.generate_color_id())
        self.update_metadata_dirty(index)
        self.refresh_table()
        self.refresh_canvas()

    def delete_segment(self, index):
        """Delete a segment after user confirmation."""
        if self.document is None or index >= len(self.document.segments):
            return
        answer = QMessageBox.question(
            self,
            "删除确认",
            "确认删除该目标及其全部 mask？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.document.remove_segment(index)
        if self.current_index == index:
            self.current_index = None
            self.clear_edit_state()
        elif self.current_index is not None and self.current_index > index:
            self.current_index -= 1
        self.refresh_table()
        self.refresh_canvas()

    def change_mode(self, button):
        """Switch the active canvas interaction mode."""
        next_mode = button.property("value")
        if next_mode != self.mode and self.has_pending_target_edit() and not self.resolve_pending_edit():
            self.set_checked_button(self.mode_group, self.mode)
            return
        self.mode = next_mode
        self.clear_edit_state()
        self.update_tool_controls()
        self.refresh_canvas()

    def change_view(self, button):
        """Switch the active image visualization mode."""
        self.view_mode = button.property("value")
        self.refresh_canvas()

    def set_checked_button(self, group, value):
        """Check a button group member by its stored value."""
        for button in group.buttons():
            if button.property("value") == value:
                button.setChecked(True)
                return

    def update_tool_controls(self):
        """Enable editing controls that apply to the current mode."""
        manual = self.mode == "brush"
        if hasattr(self, "manual_controls"):
            for control in self.manual_controls:
                control.setEnabled(manual)
        if hasattr(self, "canvas"):
            cursor = {
                "brush": Qt.CrossCursor,
                "smart": Qt.UpArrowCursor,
                "query": Qt.WhatsThisCursor,
            }[self.mode]
            self.canvas.setCursor(cursor)

    def ensure_edit_mask(self):
        """Initialize the editable mask for the selected segment."""
        if self.document is None or self.current_index is None:
            self.show_warning("无法编辑目标", "请先选择一个目标")
            return False
        if self.edit_mask is None:
            if self.mode == "smart":
                self.edit_mask = np.zeros(self.document.image_rgb.shape[:2], dtype=np.uint8)
            else:
                segment_mask = self.document.segments[self.current_index].mask
                self.edit_mask = segment_mask.copy() if segment_mask is not None else np.zeros(self.document.image_rgb.shape[:2], dtype=np.uint8)
        return True

    def clear_edit_state(self):
        """Clear pending mask, metadata, and smart prompt state."""
        self.edit_mask = None
        self.edit_dirty = False
        self.metadata_dirty = False
        self.metadata_snapshot = None
        self.prompt_points = []
        self.prompt_labels = []
        self.previous_logits = None

    def discard_edit(self):
        """Discard the pending edit for the selected segment."""
        if (
            self.metadata_snapshot is not None
            and self.document is not None
            and self.current_index is not None
            and self.current_index < len(self.document.segments)
        ):
            category_id, category_name, color_id, document_dirty = self.metadata_snapshot
            segment = self.document.segments[self.current_index]
            segment.category_id = category_id
            segment.category_name = category_name
            segment.color_id = color_id
            self.document.dirty = document_dirty
        self.clear_edit_state()
        self.refresh_table()
        self.refresh_canvas()

    def commit_current_segment(self):
        """Commit pending mask and metadata changes for the selected segment."""
        if self.document is None:
            self.show_warning("无法提交目标", "请先打开图片")
            return False
        if self.current_index is None:
            self.show_warning("无法提交目标", "请先选择一个目标")
            return False
        if self.edit_mask is None and not self.metadata_dirty:
            self.show_warning("无法提交目标", "当前目标没有待提交的编辑")
            return False
        if self.edit_mask is not None and not np.any(self.edit_mask):
            self.show_warning("无法提交目标", "当前目标没有 mask，无法提交")
            return False
        if self.edit_mask is not None:
            self.document.commit_mask(
                self.current_index,
                self.edit_mask,
            )
        self.clear_edit_state()
        self.refresh_table()
        self.refresh_canvas()
        self.log("当前目标已提交")
        return True

    def dilate_edit_mask(self):
        """Dilate the pending binary mask by one iteration."""
        if not self.ensure_edit_mask():
            return
        self.edit_mask = cv2.dilate(self.edit_mask, self.morph_kernel, iterations=1)
        self.edit_dirty = True
        self.refresh_table()
        self.refresh_canvas()

    def erode_edit_mask(self):
        """Erode the pending binary mask by one iteration."""
        if not self.ensure_edit_mask():
            return
        self.edit_mask = cv2.erode(self.edit_mask, self.morph_kernel, iterations=1)
        self.edit_dirty = True
        self.refresh_table()
        self.refresh_canvas()

    def save_document(self):
        """Commit pending work and persist the active annotation document."""
        if self.document is None:
            self.show_warning("无法存盘", "没有可存盘的图片")
            return False
        if self.has_pending_target_edit() and not self.resolve_pending_edit():
            return False
        empty = [index + 1 for index, segment in enumerate(self.document.segments) if segment.mask is None or not np.any(segment.mask)]
        if empty:
            self.show_warning("无法存盘", f"目标 {empty} 没有 mask，无法存盘")
            return False
        try:
            self.repository.save(self.document)
            self.log("标注已保存到磁盘")
            return True
        except Exception as error:
            self.log_exception("保存标注失败", error)
            return False

    def ensure_embedding(self):
        """Load or compute the active image embedding."""
        if self.document.embedding is not None:
            return True
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            embedding, elapsed_ms = self.engine.encode(self.document.image_rgb)
            self.document.embedding = embedding
            self.repository.save_embedding(self.document)
            self.log(f"图片特征生成完成：{elapsed_ms:.2f} ms")
            return True
        except Exception as error:
            self.log_exception("生成图片特征失败", error)
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def run_smart_prediction(self, x, y, positive):
        """Update the pending mask with a smart positive or negative point."""
        if not self.ensure_edit_mask() or not self.ensure_embedding():
            return
        self.prompt_points.append((x, y))
        self.prompt_labels.append(1 if positive else 0)
        try:
            mask, logits, elapsed_ms = self.engine.predict(
                self.document.embedding,
                self.document.image_rgb.shape[:2],
                self.prompt_points,
                self.prompt_labels,
                self.previous_logits,
            )
            self.edit_mask = mask
            self.previous_logits = logits
            self.edit_dirty = True
            self.refresh_table()
            self.refresh_canvas()
            self.log(f"智能分割完成：{elapsed_ms:.2f} ms")
        except Exception as error:
            self.log_exception("智能分割失败", error)

    def canvas_mouse_press(self, event):
        """Handle query, smart point, brush, and canvas pan actions."""
        if self.document is None:
            return
        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_origin = event.globalPos()
            self.canvas.setCursor(Qt.ClosedHandCursor)
            return
        position = self.image_position(event.pos())
        if position is None:
            return
        x, y = position
        if self.mode == "query":
            index = self.document.segment_index_for_pixel(x, y)
            if index is None:
                self.log("点击位置没有目标")
            else:
                self.select_segment(index)
            return
        if self.current_index is None:
            self.show_warning("无法编辑目标", "请先选择一个目标")
            return
        if self.mode == "smart" and event.button() in {Qt.LeftButton, Qt.RightButton}:
            self.run_smart_prediction(x, y, event.button() == Qt.LeftButton)
            return
        if self.mode == "brush" and event.button() in {Qt.LeftButton, Qt.RightButton}:
            if not self.ensure_edit_mask():
                return
            self.painting = 1 if event.button() == Qt.LeftButton else 0
            self.paint_at(x, y)

    def canvas_mouse_move(self, event):
        """Continue an active pan or brush stroke."""
        if self.panning and self.pan_origin is not None:
            delta = event.globalPos() - self.pan_origin
            self.pan_origin = event.globalPos()
            horizontal = self.scroll_area.horizontalScrollBar()
            vertical = self.scroll_area.verticalScrollBar()
            horizontal.setValue(horizontal.value() - delta.x())
            vertical.setValue(vertical.value() - delta.y())
            return
        if self.painting is None:
            return
        position = self.image_position(event.pos())
        if position is not None:
            self.paint_at(*position)

    def canvas_mouse_release(self, event):
        """End an active pan or brush stroke."""
        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.pan_origin = None
            self.update_tool_controls()
        self.painting = None

    def paint_at(self, x, y):
        """Paint or erase a circular area in the pending mask."""
        radius = self.brush_slider.value()
        cv2.circle(self.edit_mask, (x, y), radius, self.painting, -1)
        self.edit_dirty = True
        self.refresh_table()
        self.refresh_canvas()

    def canvas_wheel(self, event):
        """Zoom the canvas while keeping the cursor position anchored."""
        if self.document is None:
            event.ignore()
            return
        steps = event.angleDelta().y() / 120.0
        if not steps:
            return
        old_width, old_height = self.canvas_size
        anchor = event.pos()
        viewport_point = self.canvas.mapTo(self.scroll_area.viewport(), anchor)
        x_ratio = anchor.x() / max(1, old_width)
        y_ratio = anchor.y() / max(1, old_height)
        self.zoom_factor = min(
            self.maximum_zoom,
            max(self.minimum_zoom, self.zoom_factor * (self.zoom_step ** steps)),
        )
        self.apply_canvas_size()
        self.refresh_canvas()
        self.scroll_area.horizontalScrollBar().setValue(
            int(round(x_ratio * self.canvas_size[0] - viewport_point.x()))
        )
        self.scroll_area.verticalScrollBar().setValue(
            int(round(y_ratio * self.canvas_size[1] - viewport_point.y()))
        )
        event.accept()

    def image_position(self, canvas_position):
        """Map a canvas position to an image pixel."""
        if self.document is None:
            return None
        canvas_width, canvas_height = self.canvas_size
        if not (0 <= canvas_position.x() < canvas_width and 0 <= canvas_position.y() < canvas_height):
            return None
        image_height, image_width = self.document.image_rgb.shape[:2]
        x = min(image_width - 1, int((canvas_position.x() + 0.5) * image_width / canvas_width))
        y = min(image_height - 1, int((canvas_position.y() + 0.5) * image_height / canvas_height))
        return x, y

    def preview_mask(self):
        """Build the visible identifier mask including a pending edit."""
        mask = self.document.visible_mask()
        if self.current_index is None or self.edit_mask is None:
            return mask
        segment = self.document.segments[self.current_index]
        if not segment.visible:
            return mask
        mask[mask == segment.color_id] = 0
        mask[self.edit_mask.astype(bool)] = segment.color_id
        return mask

    def refresh_canvas(self):
        """Render the active image, mask, overlay, boxes, and smart prompts."""
        if self.document is None:
            return
        identifier_mask = self.preview_mask()
        color_mask = id_mask_to_rgb(identifier_mask)
        if self.view_mode == "image":
            display = self.document.image_rgb.copy()
        elif self.view_mode == "mask":
            display = color_mask
        else:
            display = cv2.addWeighted(self.document.image_rgb, 0.5, color_mask, 0.5, 0)
        pixmap = QPixmap.fromImage(qimage_from_rgb(display)).scaled(
            self.canvas_size[0],
            self.canvas_size[1],
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation if self.view_mode == "mask" else Qt.SmoothTransformation,
        )
        if self.view_mode == "overlay":
            self.draw_segment_labels(pixmap, identifier_mask)
            self.draw_prompt_points(pixmap)
        self.canvas.setPixmap(pixmap)

    def draw_segment_labels(self, pixmap, identifier_mask):
        """Draw tight boxes and category labels for visible segments."""
        painter = QPainter(pixmap)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        image_height, image_width = identifier_mask.shape
        scale_x = pixmap.width() / image_width
        scale_y = pixmap.height() / image_height
        for segment in self.document.segments:
            if not segment.visible:
                continue
            if segment.mask is None:
                continue
            active_mask = self.edit_mask if self.current_index is not None and self.document.segments[self.current_index] is segment and self.edit_mask is not None else segment.mask
            ys, xs = np.where(active_mask != 0)
            if xs.size == 0:
                continue
            red, green, blue = color_id_to_rgb(segment.color_id)
            color = QColor(red, green, blue)
            painter.setPen(QPen(color, 2))
            left = int(xs.min() * scale_x)
            top = int(ys.min() * scale_y)
            right = int((xs.max() + 1) * scale_x)
            bottom = int((ys.max() + 1) * scale_y)
            painter.drawRect(left, top, max(1, right - left), max(1, bottom - top))
            label = segment.category_name
            metrics = painter.fontMetrics()
            label_width = metrics.horizontalAdvance(label) + 8
            label_height = metrics.height() + 4
            label_top = max(0, top - label_height)
            painter.fillRect(left, label_top, label_width, label_height, color)
            text_color = Qt.black if red * 299 + green * 587 + blue * 114 > 128000 else Qt.white
            painter.setPen(text_color)
            painter.drawText(left + 4, label_top + metrics.ascent() + 2, label)
        painter.end()

    def draw_prompt_points(self, pixmap):
        """Draw positive and negative smart prompt markers."""
        if not self.prompt_points or self.document is None:
            return
        painter = QPainter(pixmap)
        image_height, image_width = self.document.image_rgb.shape[:2]
        for (x, y), label in zip(self.prompt_points, self.prompt_labels):
            point_x = int(x * pixmap.width() / image_width)
            point_y = int(y * pixmap.height() / image_height)
            color = QColor(0, 220, 0) if label == 1 else QColor(230, 30, 30)
            painter.setPen(QPen(Qt.white, 2))
            painter.setBrush(color)
            painter.drawEllipse(QPoint(point_x, point_y), 5, 5)
        painter.end()

    def color_button_text(self, color_id):
        """Return compact RGB text for a segment color button."""
        return ",".join(str(channel) for channel in color_id_to_rgb(color_id))

    def color_button_style(self, color_id):
        """Return a readable button style for a packed RGB identifier."""
        red, green, blue = color_id_to_rgb(color_id)
        foreground = "black" if red * 299 + green * 587 + blue * 114 > 128000 else "white"
        return f"background-color: rgb({red},{green},{blue}); color: {foreground}"

    def log(self, message):
        """Append an ordinary message to the application log."""
        self.log_area.append(f"<span style='color:#222'>{message}</span>")

    def show_warning(self, title, message):
        """Show a blocking interaction warning."""
        QMessageBox.warning(self, title, message, QMessageBox.Ok)

    def log_error(self, message):
        """Append an error message to the application log."""
        self.log_area.append(f"<span style='color:#c62828'>{message}</span>")

    def log_exception(self, context, error):
        """Log an exception with its traceback for diagnosis."""
        QMessageBox.critical(self, context, str(error), QMessageBox.Ok)
        self.log_error(f"{context}：{error}")
        self.log_error(traceback.format_exc().replace("\n", "<br>"))

    def closeEvent(self, event):
        """Resolve unsaved work before closing the application."""
        if self.confirm_document_transition():
            event.accept()
        else:
            event.ignore()

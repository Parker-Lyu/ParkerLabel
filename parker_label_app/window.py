import logging
import platform
import random
import sys
import traceback
from pathlib import Path

import cv2
import numpy as np
from PyQt5.QtCore import QEvent, QPoint, QRect, QRectF, QSize, Qt, QTimer, QUrl, QUrlQuery, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QActionGroup,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
    QTableWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from runtime_paths import config_directory, model_directory, portable_settings, resource_root

from .annotation_io import AnnotationRepository
from .app_info import (
    APP_DEVELOPER,
    APP_NAME,
    APP_VERSION,
    CHANGELOG_URL,
    GITEE_REPOSITORY_URL,
    MOBILE_SAM_REPOSITORY_URL,
    REPOSITORY_URL,
    SAM_REPOSITORY_URL,
    source_code_url,
)
from .canvas import AnnotationCanvas
from .category_dialog import CategoryConfigDialog
from .category_store import CategoryConfigError, CategoryConfigManager
from .editing import (
    EditSnapshot,
    apply_manual_constraints,
    arrays_equal,
    build_effective_mask_input,
    paint_brush_segment,
)
from .image_utils import color_id_to_rgb, id_mask_to_rgb, qimage_from_rgb
from .i18n import LANGUAGE_NAMES, language_manager
from .inference import SegmentationEngine
from .quality import MaskQuality, inspect_mask_quality
from .shortcut_dialog import ShortcutSettingsDialog
from .shortcuts import SPECS_BY_ID, ShortcutManager, ShortcutStore
from .update_dialog import UpdateCheckDialog


def view_control_icon(kind):
    pixmap = QPixmap(48, 48)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#344054"), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    if kind == "reset":
        for x, y, dx, dy in ((4, 4, 1, 1), (20, 4, -1, 1), (4, 20, 1, -1), (20, 20, -1, -1)):
            painter.drawLine(x, y + 5 * dy, x, y)
            painter.drawLine(x, y, x + 5 * dx, y)
    else:
        painter.drawEllipse(QRectF(4.5, 4.5, 12, 12))
        painter.drawLine(15, 15, 20, 20)
        painter.drawLine(7, 10, 14, 10)
        if kind == "in":
            painter.drawLine(10, 7, 10, 14)
    painter.end()
    return QIcon(pixmap)


class CategoryLineEdit(QLineEdit):
    def begin_edit(self):
        self.setReadOnly(False)
        self.setFocus()
        self.selectAll()

    def mouseDoubleClickEvent(self, event):
        self.begin_edit()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            self.begin_edit()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        if not self.isReadOnly():
            combo = self.parentWidget()
            if not getattr(combo, "category_submit_pending", False):
                combo.setCurrentText(combo.committed_text)
            self.setReadOnly(True)
        super().focusOutEvent(event)


class StateToggleButton(QPushButton):
    def __init__(self, text, parent=None):
        """Create a button with a colored enabled-state word."""
        super().__init__(text, parent)
        self.active = False

    def set_active(self, active):
        """Update the painted active state without changing button metrics."""
        self.active = active
        self.update()

    def paintEvent(self, event):
        """Paint only the enabled-state word in green."""
        if not self.active:
            super().paintEvent(event)
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)
        text = option.text
        prefix, separator, state_text = text.rpartition(" ")
        if not separator:
            super().paintEvent(event)
            return

        prefix += separator
        option.text = ""
        painter = QStylePainter(self)
        painter.drawControl(QStyle.CE_PushButton, option)

        content_rect = self.style().subElementRect(
            QStyle.SE_PushButtonContents, option, self
        )
        if option.state & QStyle.State_Sunken:
            content_rect.translate(
                self.style().pixelMetric(QStyle.PM_ButtonShiftHorizontal, option, self),
                self.style().pixelMetric(QStyle.PM_ButtonShiftVertical, option, self),
            )

        prefix_width = option.fontMetrics.horizontalAdvance(prefix)
        state_width = option.fontMetrics.horizontalAdvance(state_text)
        left = content_rect.center().x() - (prefix_width + state_width) // 2
        prefix_rect = QRect(left, content_rect.y(), prefix_width, content_rect.height())
        state_rect = QRect(
            left + prefix_width,
            content_rect.y(),
            state_width,
            content_rect.height(),
        )
        painter.setPen(option.palette.color(QPalette.ButtonText))
        painter.drawText(prefix_rect, Qt.AlignCenter, prefix)
        painter.setPen(QColor("#15803d"))
        painter.drawText(state_rect, Qt.AlignCenter, state_text)


class VisibilityHeader(QHeaderView):
    visibilityChanged = pyqtSignal(bool)

    def __init__(self, display_column, text, parent=None):
        """Create a header with a checkbox for global visibility."""
        super().__init__(Qt.Horizontal, parent)
        self.display_column = display_column
        self.checkbox = QCheckBox(text, self)
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
    PRIMARY_COLUMN_SPACING = 8
    WINDOWS_CATEGORY_NAME_CHARACTERS = 24
    WINDOWS_LABEL_PADDING = 16
    WINDOWS_TABLE_CELL_PADDING = 8
    QUALITY_SETTING_KEY = "interface/quality_check_enabled"
    BRUSH_SIZE_SETTING_KEY = "interface/brush_size"
    LAST_IMAGE_SETTING_KEY = "files/last_opened_image"
    TOOLTIPS_SETTING_KEY = "interface/tooltips_enabled"

    def __init__(self):
        """Initialize application services, state, and interface."""
        super().__init__()
        root = resource_root()
        configs = config_directory()
        self.settings = portable_settings()
        self.category_manager = CategoryConfigManager(
            root / "config" / "default-coco.json",
            user_directory=configs / "categories",
            settings=self.settings,
        )
        self.active_category_config_id = None
        self.active_category_config_sha256 = ""
        self.category_config_name = ""
        self.shortcut_store = ShortcutStore(self.settings)
        self.shortcut_manager = ShortcutManager(self, self.shortcut_store)
        self.shortcut_dialog = None
        self.update_dialog = None
        self.repository = AnnotationRepository(target_size=1024)
        models = model_directory()
        self.engine = SegmentationEngine(
            models / "encoder.onnx",
            models / "decoder.onnx",
            target_size=1024,
        )
        self.categories = []
        self.categories_by_name = {}
        self.all_categories_by_name = {}
        self.all_categories_by_id = {}
        self.document = None
        self.current_index = None
        self.edit_mask = None
        self.edit_dirty = False
        self.metadata_dirty = False
        self.metadata_snapshot = None
        self.prompt_points = []
        self.prompt_labels = []
        self.previous_logits = None
        self.manual_constraints = None
        self.undo_stack = []
        self.redo_stack = []
        self.history_limit = 30
        self._brush_snapshot = None
        self._brush_position = None
        self._brush_preview_base = None
        self.quality_check_enabled = self.settings.value(
            self.QUALITY_SETTING_KEY, True, type=bool
        )
        self.tooltips_enabled = self.settings.value(
            self.TOOLTIPS_SETTING_KEY, True, type=bool
        )
        self.mask_quality = MaskQuality()
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
        self.native_zoom_value = None
        self.painting = None
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.i18n = language_manager
        self.load_categories()
        self.build_ui()
        self.bind_shortcuts()
        self.build_menus()
        self.i18n.languageChanged.connect(self.retranslate_ui)
        self.reset_document_view()
        self.log(self.t("log.ready"))
        if self.shortcut_store.warnings:
            names = ", ".join(
                self.t(SPECS_BY_ID[action_id].text_key)
                for action_id in self.shortcut_store.warnings
            )
            self.log(self.t("log.shortcut_recovered", actions=names))
        if self.category_manager.warning:
            self.log(self.category_manager.warning)

    def load_categories(self, config_id=None):
        """Load enabled category records from the selected or startup configuration."""
        if config_id is None:
            config_id, data = self.category_manager.load_default()
        else:
            data = self.category_manager.load_data(config_id)
        categories = list(data.categories)
        self.active_category_config_id = config_id
        self.active_category_config_sha256 = data.content_hash
        self.category_config_name = self.category_manager.configuration(config_id).name
        self.all_categories_by_name = {category.name: category for category in categories}
        self.all_categories_by_id = {category.id: category for category in categories}
        self.categories = [category for category in categories if category.enabled]
        self.categories_by_name = {category.name: category for category in self.categories}
        if hasattr(self, "category_config_label"):
            self.update_category_config_label()

    def t(self, key, **values):
        """Return localized interface text."""
        return self.i18n.text(key, **values)

    def category_config_display_name(self):
        """Return the localized display name of the active category configuration."""
        if self.active_category_config_id == CategoryConfigManager.BUILTIN_ID:
            return self.t("category.builtin_name")
        return self.category_config_name

    def document_is_editable(self):
        """Return whether the open document matches the active immutable configuration."""
        return self.document is not None and not self.document.read_only_reason

    def update_document_access(self):
        """Bind new documents or enforce an existing annotation configuration."""
        if self.document is None:
            return
        if not self.document.annotation_loaded:
            self.document.category_config_uuid = self.active_category_config_id
            self.document.category_config_sha256 = self.active_category_config_sha256
            self.document.read_only_reason = ""
        elif self.document.category_config_uuid != self.active_category_config_id:
            self.document.read_only_reason = self.t("readonly.config_mismatch")
        elif self.document.category_config_sha256 != self.active_category_config_sha256:
            self.document.read_only_reason = self.t("readonly.hash_mismatch")
        else:
            self.document.read_only_reason = ""
        if self.document.read_only_reason:
            self.mode = "query"
            self.set_checked_button(self.mode_group, self.mode)
            self.clear_edit_state()
        self.update_editing_state()

    def update_editing_state(self):
        """Enable mutation controls only for editable documents."""
        editable = self.document_is_editable()
        self.save_button.setEnabled(editable)
        self.add_button.setEnabled(editable)
        self.commit_button.setEnabled(editable)
        self.discard_button.setEnabled(editable)
        self.update_history_controls()
        self.update_tool_controls()

    def build_ui(self):
        """Build the annotation workspace and connect user actions."""
        self.setWindowTitle("Parker Label")
        screen = QApplication.primaryScreen().availableSize()
        self.resize(max(1100, screen.width() - 80), max(720, screen.height() - 80))
        self.canvas = AnnotationCanvas(self)
        self.canvas.setText(self.t("canvas.open_image"))
        self.canvas_container = QWidget(self)
        self.canvas.setParent(self.canvas_container)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.canvas_container)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.quality_summary_label = QLabel(self.scroll_area.viewport())
        self.quality_summary_label.setTextFormat(Qt.RichText)
        self.quality_summary_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.quality_summary_label.setContentsMargins(7, 7, 7, 7)
        self.quality_summary_label.setStyleSheet(
            "color: white; background-color: rgba(0, 0, 0, 165); border-radius: 5px;"
        )
        self.quality_summary_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.quality_summary_label.hide()
        self.view_controls = QWidget(self.scroll_area.viewport())
        view_layout = QHBoxLayout(self.view_controls)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(4)
        self.reset_view_button = QToolButton(self.view_controls)
        self.zoom_in_button = QToolButton(self.view_controls)
        self.zoom_out_button = QToolButton(self.view_controls)
        for button, kind in (
            (self.reset_view_button, "reset"),
            (self.zoom_in_button, "in"),
            (self.zoom_out_button, "out"),
        ):
            button.setIcon(view_control_icon(kind))
            button.setIconSize(QSize(22, 22))
            button.setFixedSize(32, 32)
            button.setStyleSheet(
                "QToolButton { background: rgba(250, 252, 255, 240); "
                "border: 1px solid #aeb8c2; border-radius: 6px; }"
                "QToolButton:hover { background: #e7eef7; }"
                "QToolButton:pressed { background: #d6e5f5; }"
            )
            view_layout.addWidget(button)
        self.reset_view_button.clicked.connect(self.reset_canvas_view)
        self.zoom_in_button.clicked.connect(
            lambda: self.zoom_canvas_at_center(self.zoom_step)
        )
        self.zoom_out_button.clicked.connect(
            lambda: self.zoom_canvas_at_center(1 / self.zoom_step)
        )
        self.view_controls.adjustSize()
        self.view_controls.move(8, 8)
        self.view_controls.hide()
        self.scroll_area.viewport().installEventFilter(self)
        controls = QVBoxLayout()
        self.primary_controls = self.build_primary_controls()
        self.tool_controls = self.build_tool_controls()
        controls.addLayout(self.primary_controls)
        controls.addLayout(self.tool_controls)
        if sys.platform == "win32":
            controls.addSpacing(10)
        self.table = self.build_segment_table()
        controls.addWidget(self.table, 1)
        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(110)
        self.log_area.document().setMaximumBlockCount(500)
        controls.addWidget(self.log_area)
        self.control_panel = QWidget(self)
        self.control_panel.setLayout(controls)
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(sys.platform == "darwin")
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.scroll_area, 1)
        content_layout.addWidget(self.control_panel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.menu_bar)
        layout.addLayout(content_layout, 1)
        self.resize_segment_table_columns()

    def build_primary_controls(self):
        """Create the compact primary action grid."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        button_layout = QGridLayout()
        button_layout.setHorizontalSpacing(self.PRIMARY_COLUMN_SPACING)
        button_layout.setVerticalSpacing(6)
        self.open_button = QPushButton()
        self.quality_button = StateToggleButton("")
        self.quality_button.set_active(self.quality_check_enabled)
        self.category_button = QPushButton()
        self.save_button = QPushButton()
        self.open_button.clicked.connect(self.choose_image)
        self.quality_button.clicked.connect(self.toggle_quality_check)
        self.category_button.clicked.connect(self.configure_categories)
        self.save_button.clicked.connect(self.save_document)
        self.category_config_label = QLabel()
        self.category_config_label.setTextFormat(Qt.PlainText)
        self.category_config_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.update_primary_control_text()
        self.resize_primary_buttons()
        button_layout.addWidget(self.open_button, 0, 0)
        button_layout.addWidget(self.quality_button, 0, 1)
        button_layout.addWidget(self.category_button, 1, 0)
        button_layout.addWidget(self.save_button, 1, 1)
        button_layout.setColumnStretch(2, 1)
        layout.addLayout(button_layout)
        layout.addWidget(self.category_config_label, 0, Qt.AlignLeft)
        if sys.platform == "win32":
            layout.addSpacing(10)
        return layout

    def build_tool_controls(self):
        """Create drawing, viewing, morphology, and brush controls."""
        outer = QVBoxLayout()
        if sys.platform == "win32":
            outer.setSpacing(14)

        self.edit_group = QGroupBox()
        edit_layout = QVBoxLayout(self.edit_group)
        edit_layout.setSpacing(2)
        self.undo_button = QPushButton()
        self.redo_button = QPushButton()
        self.add_button = QPushButton()
        self.commit_button = QPushButton()
        self.discard_button = QPushButton()
        self.undo_button.clicked.connect(self.undo_edit)
        self.redo_button.clicked.connect(self.redo_edit)
        self.add_button.clicked.connect(self.add_segment)
        self.commit_button.clicked.connect(self.commit_current_segment)
        self.discard_button.clicked.connect(self.discard_edit)
        undo_redo_layout = QHBoxLayout()
        undo_redo_layout.addWidget(self.undo_button)
        undo_redo_layout.addWidget(self.redo_button)
        edit_layout.addLayout(undo_redo_layout)
        edit_layout.addWidget(self.add_button)
        edit_layout.addWidget(self.discard_button)
        edit_layout.addWidget(self.commit_button)

        self.view_group_box = QGroupBox()
        view_layout = QHBoxLayout(self.view_group_box)
        self.view_group = QButtonGroup(self)
        views = ("image", "mask", "overlay")
        for value in views:
            button = QRadioButton()
            button.setProperty("value", value)
            self.view_group.addButton(button)
            view_layout.addWidget(button, 1, Qt.AlignCenter)
            if value == self.view_mode:
                button.setChecked(True)
        self.view_group.buttonClicked.connect(self.change_view)

        self.interaction_group = QGroupBox()
        interaction_layout = QVBoxLayout(self.interaction_group)
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        modes = ("smart", "brush", "query")
        for value in modes:
            button = QRadioButton()
            button.setProperty("value", value)
            self.mode_group.addButton(button)
            mode_layout.addWidget(button)
            if value == self.mode:
                button.setChecked(True)
        self.mode_group.buttonClicked.connect(self.change_mode)
        mode_layout.addStretch(1)

        brush_layout = QHBoxLayout()
        self.brush_label = QLabel()
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 50)
        try:
            brush_size = int(self.settings.value(self.BRUSH_SIZE_SETTING_KEY, 3))
        except (TypeError, ValueError):
            brush_size = 3
        self.brush_slider.setValue(max(1, min(50, brush_size)))
        self.brush_slider.valueChanged.connect(
            lambda value: self.brush_label.setText(
                self.t("manual.brush_size", value=value)
            )
        )
        self.brush_slider.valueChanged.connect(lambda _value: self.canvas.update())
        self.brush_slider.valueChanged.connect(self.save_brush_size)
        brush_layout.addWidget(self.brush_label)
        brush_layout.addWidget(self.brush_slider, 1)

        morphology_layout = QHBoxLayout()
        self.erode_button = QPushButton()
        self.dilate_button = QPushButton()
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
        for group in (self.edit_group, self.view_group_box, self.interaction_group):
            group.setStyleSheet(group_style)
        lower_row = QHBoxLayout()
        self.tool_control_row = lower_row
        lower_row.addWidget(self.edit_group)
        lower_row.addWidget(self.interaction_group)
        lower_row.addStretch(1)
        outer.addWidget(self.view_group_box, 0, Qt.AlignLeft)
        outer.addLayout(lower_row)
        self.update_tool_control_text()
        self.update_tool_controls()
        self.update_tooltips()
        return outer

    def build_segment_table(self):
        """Create the segment table used to edit document-backed records."""
        table = QTableWidget(0, 6, self)
        header = VisibilityHeader(self.COL_SHOW, self.t("table.show"), table)
        table.setHorizontalHeader(header)
        self.update_table_headers(table)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setMinimumSectionSize(44)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        header.visibilityChanged.connect(self.set_all_segments_visible)
        table.cellClicked.connect(self.handle_segment_cell_click)
        header.update_checkbox_geometry()
        return table

    def update_primary_control_text(self):
        """Refresh localized text for primary and status controls."""
        self.open_button.setText(self.t("main.open_image"))
        self.quality_button.setText(
            self.t("main.quality.on" if self.quality_check_enabled else "main.quality.off")
        )
        self.category_button.setText(self.t("main.category_config"))
        self.save_button.setText(self.t("main.save_disk"))
        self.update_category_config_label()

    def update_category_config_label(self):
        """Show the active configuration on one line."""
        name = self.category_config_display_name()
        label = self.t("category.current", name=name)
        self.category_config_label.setToolTip(label)
        width = self.category_config_label.width() - 4
        if width > 0:
            prefix, separator, suffix = label.partition(name)
            if sys.platform == "win32" and separator:
                fixed_width = self.category_config_label.fontMetrics().horizontalAdvance(
                    prefix + suffix
                )
                name = self.category_config_label.fontMetrics().elidedText(
                    name, Qt.ElideRight, max(0, width - fixed_width)
                )
                label = prefix + name + suffix
            else:
                label = self.category_config_label.fontMetrics().elidedText(
                    label, Qt.ElideRight, width
                )
        self.category_config_label.setText(label)

    def resize_primary_buttons(self):
        """Keep the four primary buttons aligned across languages and toggle states."""
        buttons = (
            self.open_button,
            self.quality_button,
            self.category_button,
            self.save_button,
        )
        width = max(button.sizeHint().width() for button in buttons)
        height = max(button.sizeHint().height() for button in buttons)
        padding = self.quality_button.sizeHint().width() - self.quality_button.fontMetrics().horizontalAdvance(
            self.quality_button.text()
        )
        width = max(
            width,
            *(
                self.quality_button.fontMetrics().horizontalAdvance(self.t(key)) + padding
                for key in ("main.quality.off", "main.quality.on")
            ),
        )
        for button in buttons:
            button.setFixedSize(width, height)
        label_width = width * 2 + self.PRIMARY_COLUMN_SPACING
        if sys.platform == "win32":
            name = self.category_config_display_name()
            label = self.t("category.current", name=name)
            prefix, separator, suffix = label.partition(name)
            if separator:
                metrics = self.category_config_label.fontMetrics()
                name_width = min(
                    metrics.horizontalAdvance(name),
                    metrics.horizontalAdvance(
                        "M" * self.WINDOWS_CATEGORY_NAME_CHARACTERS
                    ),
                )
                label_width = max(
                    label_width,
                    metrics.horizontalAdvance(prefix + suffix)
                    + name_width
                    + self.WINDOWS_LABEL_PADDING,
                )
        self.category_config_label.setFixedWidth(label_width)
        self.update_category_config_label()

    def update_tool_control_text(self):
        """Refresh localized text for editing and viewing controls."""
        self.edit_group.setTitle(self.t("main.group.edit"))
        self.view_group_box.setTitle(self.t("main.group.view"))
        self.interaction_group.setTitle(self.t("main.group.interaction"))
        self.undo_button.setText(self.t("main.undo"))
        self.redo_button.setText(self.t("main.redo"))
        self.add_button.setText(self.t("main.add_target"))
        self.commit_button.setText(self.t("main.commit_target"))
        self.discard_button.setText(self.t("main.discard_changes"))
        for button in self.view_group.buttons():
            button.setText(self.t(f"main.view.{button.property('value')}"))
        for button in self.mode_group.buttons():
            button.setText(self.t(f"main.mode.{button.property('value')}"))
        self.brush_label.setText(
            self.t("manual.brush_size", value=self.brush_slider.value())
        )
        self.erode_button.setText(self.t("manual.erode"))
        self.dilate_button.setText(self.t("manual.dilate"))

    def update_table_headers(self, table=None):
        """Refresh localized segment table headings."""
        table = table or self.table
        table.setHorizontalHeaderLabels(
            [
                "ID",
                self.t("table.edit"),
                "",
                self.t("table.category"),
                self.t("table.color"),
                self.t("table.delete"),
            ]
        )
        table.horizontalHeader().checkbox.setText(self.t("table.show"))

    def toggle_tooltips(self, _checked=False):
        """Toggle contextual interface hints."""
        self.tooltips_enabled = not self.tooltips_enabled
        self.settings.setValue(self.TOOLTIPS_SETTING_KEY, self.tooltips_enabled)
        self.settings.sync()
        if hasattr(self, "tooltip_action"):
            self.tooltip_action.setChecked(self.tooltips_enabled)
        self.update_tooltips()

    def update_tooltips(self):
        """Refresh localized hints for controls that need extra clarification."""
        tooltip_map = (
            (self.open_button, None, "open_image"),
            (self.quality_button, "tooltip.quality", "toggle_quality"),
            (self.category_button, None, "category_config"),
            (self.save_button, None, "save_document"),
            (self.undo_button, None, "undo_edit"),
            (self.redo_button, None, "redo_edit"),
            (self.add_button, None, "add_target"),
            (self.commit_button, "tooltip.commit_target", "commit_target"),
            (self.discard_button, "tooltip.discard_changes", "discard_edit"),
            (self.erode_button, "tooltip.erode", "erode"),
            (self.dilate_button, "tooltip.dilate", "dilate"),
        )
        for control, key, action_id in tooltip_map:
            base = self.t(key) if key else ""
            control.setToolTip(self.shortcut_tooltip(base, action_id))
        for button in self.mode_group.buttons():
            key = f"tooltip.mode.{button.property('value')}"
            action_id = {
                "smart": "mode_smart",
                "brush": "mode_brush",
                "query": "mode_query",
            }[button.property("value")]
            button.setToolTip(self.shortcut_tooltip(self.t(key), action_id))
        for button in self.view_group.buttons():
            action_id = f"view_{button.property('value')}"
            button.setToolTip(self.shortcut_tooltip("", action_id))
        for button, key in (
            (self.reset_view_button, "canvas.reset_view"),
            (self.zoom_in_button, "canvas.zoom_in"),
            (self.zoom_out_button, "canvas.zoom_out"),
        ):
            label = self.t(key)
            button.setAccessibleName(label)
            button.setToolTip(label if self.tooltips_enabled else "")

    def shortcut_tooltip(self, base, action_id):
        """Append an active shortcut hint when interface tips are enabled."""
        if not self.tooltips_enabled:
            return ""
        shortcut = self.shortcut_manager.shortcut_text(action_id)
        hint = self.t("tooltip.shortcut", shortcut=shortcut) if shortcut else ""
        return "\n".join(part for part in (base, hint) if part)

    def retranslate_ui(self, _language=None):
        """Refresh visible interface text after a language change."""
        for action in self.language_actions.actions():
            action.setChecked(action.data() == self.i18n.language)
        self.retranslate_menus()
        self.update_primary_control_text()
        self.update_tool_control_text()
        for group in (self.edit_group, self.interaction_group):
            for index in range(group.layout().count()):
                child_layout = group.layout().itemAt(index).layout()
                if child_layout is not None:
                    child_layout.invalidate()
            group.layout().invalidate()
        self.update_table_headers()
        self.update_tooltips()
        if self.document is None:
            self.canvas.setText(self.t("canvas.open_image"))
            if self.log_area.document().blockCount() == 1:
                self.log_area.setPlainText(self.t("log.ready"))
        self.refresh_table()
        self.resize_primary_buttons()
        self.primary_controls.invalidate()
        self.primary_controls.activate()
        self.tool_control_row.invalidate()
        self.tool_controls.invalidate()
        self.tool_controls.activate()
        self.resize_segment_table_columns()
        self.update_quality_overlay()
        self.update_view_controls()

    def build_menus(self):
        """Create Settings and Help menus with explicit native menu roles."""
        self.settings_menu = self.menu_bar.addMenu("")
        self.shortcut_settings_action = QAction(self)
        self.shortcut_settings_action.setMenuRole(QAction.NoRole)
        self.shortcut_settings_action.triggered.connect(self.open_shortcut_settings)
        self.settings_menu.addAction(self.shortcut_settings_action)
        self.settings_menu.addSeparator()

        self.language_menu = QMenu(self.settings_menu)
        self.language_actions = QActionGroup(self.language_menu)
        self.language_actions.setExclusive(True)
        for code, name in LANGUAGE_NAMES.items():
            action = self.language_menu.addAction(name)
            action.setData(code)
            action.setCheckable(True)
            action.setChecked(code == self.i18n.language)
            action.setMenuRole(QAction.NoRole)
            self.language_actions.addAction(action)
        self.language_actions.triggered.connect(
            lambda action: self.i18n.set_language(action.data())
        )
        self.settings_menu.addMenu(self.language_menu)

        self.tooltip_action = QAction(self)
        self.tooltip_action.setCheckable(True)
        self.tooltip_action.setChecked(self.tooltips_enabled)
        self.tooltip_action.setMenuRole(QAction.NoRole)
        self.tooltip_action.triggered.connect(self.toggle_tooltips)
        self.settings_menu.addAction(self.tooltip_action)

        self.help_menu = self.menu_bar.addMenu("")
        self.github_action = QAction(self)
        self.github_action.setMenuRole(QAction.NoRole)
        self.github_action.triggered.connect(lambda: self.open_external_url(REPOSITORY_URL))
        self.help_menu.addAction(self.github_action)
        self.changelog_action = QAction(self)
        self.changelog_action.setMenuRole(QAction.NoRole)
        self.changelog_action.triggered.connect(lambda: self.open_external_url(CHANGELOG_URL))
        self.help_menu.addAction(self.changelog_action)
        self.check_updates_action = QAction(self)
        self.check_updates_action.setMenuRole(QAction.NoRole)
        self.check_updates_action.triggered.connect(self.open_update_check)
        self.help_menu.addAction(self.check_updates_action)
        self.licenses_action = QAction(self)
        self.licenses_action.setMenuRole(QAction.NoRole)
        self.licenses_action.triggered.connect(self.open_source_licenses)
        self.help_menu.addAction(self.licenses_action)
        self.about_action = QAction(self)
        self.about_action.setMenuRole(QAction.NoRole)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_action)

        if sys.platform == "darwin":
            self.quit_action = QAction(self)
            self.quit_action.setMenuRole(QAction.QuitRole)
            self.quit_action.triggered.connect(self.close)
            self.settings_menu.addAction(self.quit_action)
        self.retranslate_menus()

    def retranslate_menus(self):
        """Refresh menu labels and visible shortcut markers."""
        if not hasattr(self, "settings_menu"):
            return
        self.settings_menu.setTitle(self.t("menu.settings"))
        self.help_menu.setTitle(self.t("menu.help"))
        self.language_menu.setTitle(self.t("menu.language"))
        self.tooltip_action.setText(self.t("menu.tooltips"))
        self.github_action.setText(self.t("menu.github"))
        self.changelog_action.setText(self.t("menu.changelog"))
        self.check_updates_action.setText(self.t("menu.check_updates"))
        self.licenses_action.setText(self.t("menu.licenses"))
        self.about_action.setText(self.t("menu.about"))
        self.shortcut_settings_action.setText(
            self.menu_text("menu.shortcut_settings", "shortcut_settings")
        )
        if hasattr(self, "quit_action"):
            self.quit_action.setText(self.t("menu.quit"))

    def menu_text(self, key, action_id):
        """Return menu text with a visual shortcut marker."""
        shortcut = self.shortcut_manager.shortcut_text(action_id)
        return self.t(key) if not shortcut else f"{self.t(key)}\t{shortcut}"

    def open_external_url(self, url):
        """Open an application link in the system browser."""
        if not QDesktopServices.openUrl(QUrl(url)):
            self.show_warning(self.t("link.open_failed"), self.t("link.open_failed_detail"))

    def open_source_licenses(self):
        """Open the bundled license page without requiring network access."""
        path = resource_root() / "third_party_licenses" / "OPEN_SOURCE_LICENSES.html"
        url = QUrl.fromLocalFile(str(path))
        query = QUrlQuery()
        query.addQueryItem("version", APP_VERSION or self.t("about.development_build"))
        if sys.platform == "darwin":
            query.addQueryItem("platform", f"macos-{platform.machine().lower()}")
        elif sys.platform == "win32":
            machine = platform.machine().lower()
            query.addQueryItem("platform", "windows-x64" if machine in {"amd64", "x86_64"} else f"windows-{machine}")
        query.addQueryItem("source", source_code_url())
        url.setQuery(query)
        if not QDesktopServices.openUrl(url):
            self.show_warning(self.t("link.open_failed"), self.t("link.open_failed_detail"))

    def show_about_dialog(self):
        """Show application metadata without requiring network access."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("menu.about"))
        layout = QVBoxLayout(dialog)
        title = QLabel(f"<b>{APP_NAME}</b>")
        description = QLabel(self.t("about.description"))
        performance = QLabel(self.t("about.performance"))
        performance.setTextFormat(Qt.RichText)
        model = QLabel(self.t("about.model"))
        descriptions = (description, performance, model)
        for description in descriptions:
            description.setWordWrap(True)
            description.setFixedWidth(620)
            description.setMinimumHeight(description.sizeHint().height())
        details = QLabel(
            self.t(
                "about.details",
                version=APP_VERSION or self.t("about.development_build"),
                developer=APP_DEVELOPER,
            )
        )
        project_links_title = QLabel(self.t("about.project_links"))
        project_links = QLabel(
            f'<a href="{REPOSITORY_URL}">{self.t("menu.github")}</a>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<a href="{GITEE_REPOSITORY_URL}">{self.t("menu.gitee")}</a>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<a href="{CHANGELOG_URL}">{self.t("menu.changelog")}</a>'
        )
        model_references_title = QLabel(self.t("about.model_references"))
        model_references = QLabel(
            f'<a href="{MOBILE_SAM_REPOSITORY_URL}">MobileSAM</a>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;'
            f'<a href="{SAM_REPOSITORY_URL}">Segment Anything (SAM)</a>'
        )
        legal_title = QLabel(self.t("about.legal"))
        licenses_link = QLabel(f'<a href="licenses">{self.t("menu.licenses")}</a>')
        for links in (project_links, model_references):
            links.setTextFormat(Qt.RichText)
            links.setTextInteractionFlags(Qt.TextBrowserInteraction)
            links.setOpenExternalLinks(False)
            links.linkActivated.connect(self.open_external_url)
        licenses_link.setTextFormat(Qt.RichText)
        licenses_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        licenses_link.setOpenExternalLinks(False)
        licenses_link.linkActivated.connect(lambda _url: self.open_source_licenses())
        for heading in (project_links_title, model_references_title, legal_title):
            font = heading.font()
            font.setBold(True)
            heading.setFont(font)
        update_button = QPushButton(self.t("menu.check_updates"))
        update_button.clicked.connect(dialog.accept)
        update_button.clicked.connect(lambda: QTimer.singleShot(0, self.open_update_check))
        close_button = QPushButton(self.t("common.close"))
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(title)
        for description in descriptions:
            layout.addWidget(description)
        layout.addWidget(details)
        layout.addWidget(project_links_title)
        layout.addWidget(project_links)
        layout.addWidget(model_references_title)
        layout.addWidget(model_references)
        layout.addWidget(legal_title)
        layout.addWidget(licenses_link)
        button_layout = QHBoxLayout()
        button_layout.addWidget(update_button)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        dialog.setModal(True)
        dialog.exec_()

    def open_update_check(self):
        """Open one non-blocking update check window."""
        if self.update_dialog is not None and self.update_dialog.isVisible():
            self.update_dialog.raise_()
            self.update_dialog.activateWindow()
            return
        self.update_dialog = UpdateCheckDialog(self, self.open_external_url)
        self.update_dialog.finished.connect(
            lambda _result: setattr(self, "update_dialog", None)
        )
        self.update_dialog.show()
        self.update_dialog.start()

    def bind_shortcuts(self):
        """Bind configurable shortcut IDs to existing application actions."""
        bind = self.shortcut_manager.bind
        bind("open_image", self.choose_image)
        bind("save_document", self.save_document, lambda: self.save_button.isEnabled())
        bind("shortcut_settings", self.open_shortcut_settings)
        bind("undo_edit", self.undo_edit, lambda: self.undo_button.isEnabled())
        bind("redo_edit", self.redo_edit, lambda: self.redo_button.isEnabled())
        bind("add_target", self.add_segment, lambda: self.add_button.isEnabled())
        bind("commit_target", self.commit_current_segment, lambda: self.commit_button.isEnabled())
        bind("discard_edit", self.discard_edit, lambda: self.discard_button.isEnabled())
        bind(
            "delete_target",
            self.delete_current_target,
            lambda: self.document_is_editable() and self.current_index is not None,
        )
        bind("mode_smart", lambda: self.activate_mode("smart"), lambda: self.mode_enabled("smart"))
        bind("mode_brush", lambda: self.activate_mode("brush"), lambda: self.mode_enabled("brush"))
        bind("mode_query", lambda: self.activate_mode("query"), lambda: self.mode_enabled("query"))
        bind("view_image", lambda: self.activate_view("image"), lambda: self.document is not None)
        bind("view_mask", lambda: self.activate_view("mask"), lambda: self.document is not None)
        bind("view_overlay", lambda: self.activate_view("overlay"), lambda: self.document is not None)
        bind("brush_smaller", lambda: self.adjust_brush(-1), lambda: self.brush_slider.isEnabled())
        bind("brush_larger", lambda: self.adjust_brush(1), lambda: self.brush_slider.isEnabled())
        bind("erode", self.erode_edit_mask, lambda: self.erode_button.isEnabled())
        bind("dilate", self.dilate_edit_mask, lambda: self.dilate_button.isEnabled())
        bind("toggle_quality", self.toggle_quality_check)
        bind("category_config", self.configure_categories)

    def open_shortcut_settings(self):
        """Open one modal shortcut settings window."""
        if self.shortcut_dialog is not None and self.shortcut_dialog.isVisible():
            self.shortcut_dialog.raise_()
            self.shortcut_dialog.activateWindow()
            return
        self.shortcut_dialog = ShortcutSettingsDialog(self, self.shortcut_manager)
        self.shortcut_dialog.finished.connect(
            lambda _result: setattr(self, "shortcut_dialog", None)
        )
        self.shortcut_dialog.open()

    def shortcuts_changed(self):
        """Refresh UI elements that show active shortcut bindings."""
        self.retranslate_menus()
        self.update_tooltips()

    def mode_enabled(self, value):
        """Return whether a mode can currently be entered."""
        if self.document is None:
            return False
        for button in self.mode_group.buttons():
            if button.property("value") == value:
                return button.isEnabled()
        return False

    def activate_mode(self, value):
        """Switch mode through the same handler used by radio buttons."""
        for button in self.mode_group.buttons():
            if button.property("value") == value:
                self.change_mode(button)
                self.set_checked_button(self.mode_group, self.mode)
                return

    def activate_view(self, value):
        """Switch view through the same handler used by radio buttons."""
        for button in self.view_group.buttons():
            if button.property("value") == value:
                self.change_view(button)
                self.set_checked_button(self.view_group, self.view_mode)
                return

    def adjust_brush(self, delta):
        """Move the brush slider by one unit."""
        self.brush_slider.setValue(self.brush_slider.value() + delta)

    def delete_current_target(self):
        """Delete only the explicitly selected current target."""
        if self.current_index is not None:
            self.delete_segment(self.current_index)

    def eventFilter(self, watched, event):
        """Keep viewport overlays aligned when the image viewport changes size."""
        if (
            hasattr(self, "scroll_area")
            and watched is self.scroll_area.viewport()
            and event.type() == QEvent.Resize
        ):
            self.update_canvas_container()
            self.position_quality_overlay()
            self.view_controls.raise_()
        return super().eventFilter(watched, event)

    def position_quality_overlay(self):
        """Anchor the quality summary to the viewport's upper-right corner."""
        if not hasattr(self, "quality_summary_label"):
            return
        margin = 8
        viewport = self.scroll_area.viewport()
        left = max(margin, viewport.width() - self.quality_summary_label.width() - margin)
        self.quality_summary_label.move(left, margin)

    def update_quality_overlay(self):
        """Refresh the viewport-level mask quality summary."""
        if not self.quality_check_enabled or self.document is None:
            self.quality_summary_label.hide()
            return
        if self.current_quality_mask() is None:
            text = self.t("quality.no_target")
        else:
            regions_text = self.t(
                "quality.regions", regions=self.mask_quality.mask_region_count
            )
            if self.mask_quality.mask_region_count > 1:
                regions_text = f'<span style="color:#ff5252;">{regions_text}</span>'
            holes_text = self.t("quality.holes", holes=self.mask_quality.hole_count)
            if self.mask_quality.hole_count > 0:
                holes_text = f'<span style="color:#ff5252;">{holes_text}</span>'
            text = f"{regions_text}&nbsp;&nbsp;{holes_text}"
        self.quality_summary_label.setText(text)
        self.quality_summary_label.adjustSize()
        self.position_quality_overlay()
        self.quality_summary_label.raise_()
        self.quality_summary_label.show()

    def reset_document_view(self):
        """Reset table and canvas state when no document is active."""
        self.current_index = None
        self.mode = "query"
        self.set_checked_button(self.mode_group, self.mode)
        self.clear_edit_state()
        self.table.setRowCount(0)
        self.canvas.setText(self.t("canvas.open_image"))
        self.canvas.setFixedSize(640, 480)
        self.update_canvas_container()
        self.update_editing_state()
        self.update_quality_overlay()
        self.update_view_controls()

    def update_view_controls(self):
        self.view_controls.setVisible(self.document is not None)
        self.view_controls.raise_()

    def choose_image(self):
        """Open a file picker and load the selected image."""
        last_image = self.settings.value(self.LAST_IMAGE_SETTING_KEY, "", type=str)
        directory = Path(last_image).expanduser().parent if last_image else None
        while directory is not None and not directory.is_dir():
            parent = directory.parent
            directory = parent if parent != directory else None
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.t("main.open_image"),
            str(directory) if directory else "",
            self.t("dialog.image_filter"),
        )
        if path:
            self.open_image(path)

    def save_brush_size(self, value):
        """Remember the current brush size."""
        self.settings.setValue(self.BRUSH_SIZE_SETTING_KEY, value)
        self.settings.sync()

    def open_image(self, path):
        """Open an image and its existing annotation artifacts."""
        suffix = Path(path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".bmp"}:
            self.show_warning(
                self.t("dialog.open_image_failed"),
                self.t("dialog.unsupported_image"),
            )
            return
        if not self.confirm_document_transition():
            return
        try:
            self.document = self.repository.open(Path(path))
            self.resolve_open_document_configuration()
            self.current_index = None
            self.clear_edit_state()
            self.update_mask_quality()
            self.zoom_factor = 1.0
            self.calculate_base_canvas_size()
            self.refresh_table()
            self.refresh_canvas()
            self.update_editing_state()
            self.update_view_controls()
            self.center_canvas_view()
            self.settings.setValue(
                self.LAST_IMAGE_SETTING_KEY, str(self.document.image_path.resolve())
            )
            self.settings.sync()
            self.log(self.t("log.image_opened", name=self.document.image_path.name))
            if self.document.read_only_reason:
                self.show_warning(
                    self.t("readonly.title"),
                    self.document.read_only_reason,
                )
                self.log(self.document.read_only_reason)
            elif self.document.embedding is None:
                self.ensure_embedding()
            else:
                self.log(self.t("log.embedding_loaded"))
        except Exception as error:
            self.log_exception(self.t("error.open_image"), error)

    def resolve_open_document_configuration(self):
        """Resolve the exact configuration required by a loaded annotation."""
        if not self.document.annotation_loaded:
            self.update_document_access()
            return
        config_id = self.document.category_config_uuid
        try:
            self.category_manager.configuration(config_id)
        except CategoryConfigError:
            self.document.read_only_reason = self.t(
                "readonly.config_missing", uuid=config_id
            )
            return
        if config_id != self.active_category_config_id:
            config = self.category_manager.configuration(config_id)
            config_name = (
                self.t("category.builtin_name")
                if config.builtin
                else config.name
            )
            answer = QMessageBox.question(
                self,
                self.t("dialog.switch_category_title"),
                self.t("dialog.switch_category_confirm", name=config_name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                self.load_categories(config_id)
        self.update_document_access()

    def confirm_document_transition(self):
        """Ask how to handle unsaved work before replacing the document."""
        if self.document is None or not (self.document.dirty or self.has_pending_target_edit()):
            return True
        answer = QMessageBox.question(
            self,
            self.t("dialog.unsaved_document"),
            self.t("dialog.unsaved_document_confirm"),
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
        self.update_canvas_container()

    def update_canvas_container(self):
        """Keep panning space around the canvas at every zoom level."""
        viewport = self.scroll_area.viewport()
        horizontal_margin = viewport.width() // 2 if self.document is not None else 0
        vertical_margin = viewport.height() // 2 if self.document is not None else 0
        self.canvas.move(horizontal_margin, vertical_margin)
        self.canvas_container.resize(
            self.canvas.width() + 2 * horizontal_margin,
            self.canvas.height() + 2 * vertical_margin,
        )

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
            category.setEnabled(
                self.document_is_editable() and index == self.current_index
            )
            category.activated[str].connect(
                lambda name, row=index: self.set_segment_category(row, name)
            )
            category.lineEdit().returnPressed.connect(
                lambda row=index, combo=category: self.submit_segment_category(row, combo)
            )
            self.table.setCellWidget(index, self.COL_CATEGORY, category)
            color = QPushButton(self.color_button_text(segment.color_id))
            color.setStyleSheet(self.color_button_style(segment.color_id))
            color.setEnabled(
                self.document_is_editable() and index == self.current_index
            )
            color.clicked.connect(lambda checked=False, row=index: self.assign_random_color(row))
            self.table.setCellWidget(index, self.COL_COLOR, color)
            delete = QPushButton(self.t("common.delete"))
            delete.setEnabled(self.document_is_editable())
            delete.clicked.connect(lambda checked=False, row=index: self.delete_segment(row))
            self.table.setCellWidget(index, self.COL_DELETE, delete)
        if self.current_index is not None and self.current_index < self.table.rowCount():
            self.table.selectRow(self.current_index)
        self.update_visibility_header()
        self.resize_segment_table_columns()

    def resize_segment_table_columns(self):
        """Size table columns and the control panel from their contents."""
        self.table.resizeColumnsToContents()
        visibility_width = self.table.horizontalHeader().checkbox.sizeHint().width() + 8
        self.table.setColumnWidth(
            self.COL_SHOW,
            max(self.table.columnWidth(self.COL_SHOW), visibility_width),
        )
        category_probe = QComboBox()
        selected_categories = (
            [segment.category_name for segment in self.document.segments]
            if self.document is not None
            else []
        )
        probe_categories = selected_categories
        if sys.platform == "win32":
            probe_categories = [category.name for category in self.categories]
            probe_categories += selected_categories
        category_probe.addItems(
            list(dict.fromkeys(probe_categories)) or [self.t("table.category")]
        )
        category_width = category_probe.sizeHint().width()
        if sys.platform == "win32":
            category_width += self.WINDOWS_TABLE_CELL_PADDING
        self.table.setColumnWidth(self.COL_CATEGORY, category_width)
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
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setLineEdit(CategoryLineEdit(combo))
        combo.lineEdit().setReadOnly(True)
        combo.setToolTip(self.t("table.category_edit_hint"))
        combo.lineEdit().setToolTip(self.t("table.category_edit_hint"))
        names = [category.name for category in self.categories]
        if current_name and current_name not in names:
            names.insert(0, current_name)
        combo.addItems(names)
        combo.setCurrentText(current_name)
        combo.committed_text = current_name
        for index, name in enumerate(names):
            category = self.categories_by_name.get(name)
            if category is not None:
                description = category.description or self.t("category.no_description")
                combo.setItemData(index, f"{category.supercategory}\n{description}", Qt.ToolTipRole)
        return combo

    def submit_segment_category(self, index, combo):
        if getattr(combo, "category_submit_pending", False):
            return
        combo.category_submit_pending = True
        QTimer.singleShot(0, lambda: self.finish_segment_category(index, combo))

    def finish_segment_category(self, index, combo):
        combo.category_submit_pending = False
        name = combo.currentText()
        if combo.findText(name, Qt.MatchExactly) < 0:
            self.show_warning(
                self.t("table.category_missing_title"),
                self.t("table.category_missing", name=name),
            )
            if self.document is not None and index < len(self.document.segments):
                combo.setCurrentText(self.document.segments[index].category_name)
            self.table.setFocus()
            return
        self.set_segment_category(index, name)
        combo.committed_text = name
        combo.lineEdit().setReadOnly(True)
        self.table.setFocus()

    def configure_categories(self):
        """Open the category manager and apply the selected configuration."""
        try:
            if self.current_index is not None and not self.resolve_pending_edit():
                return
            dialog = CategoryConfigDialog(
                self.category_manager,
                self.active_category_config_id,
                apply_validator=self.confirm_category_application,
                parent=self,
            )
            dialog.configurationApplied.connect(self.apply_category_config)
            dialog.exec_()
        except Exception as error:
            self.log_exception(self.t("error.category_config_open"), error)

    def confirm_category_application(self, config_id):
        """Confirm that a bound annotation may become read-only."""
        if (
            self.document is None
            or (not self.document.annotation_loaded and not self.document.segments)
            or self.document.category_config_uuid == config_id
        ):
            return True
        if self.document.dirty:
            answer = QMessageBox.question(
                self,
                self.t("dialog.save_before_category_title"),
                self.t("dialog.save_before_category_confirm"),
                QMessageBox.Yes | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes or not self.save_document():
                return False
        answer = QMessageBox.warning(
            self,
            self.t("dialog.change_category_title"),
            self.t("dialog.change_category_readonly"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def apply_category_config(self, config_id):
        """Apply one configuration and update document access state."""
        self.load_categories(config_id)
        self.update_document_access()
        self.refresh_table()
        self.refresh_canvas()
        message = self.t(
            "log.category_applied",
            name=self.category_config_display_name(),
            count=len(self.categories),
        )
        self.log(message)
        if self.document is not None and self.document.read_only_reason:
            self.show_warning(self.t("readonly.title"), self.document.read_only_reason)

    def add_segment(self):
        """Add an empty segment using the first enabled category."""
        if self.document is None:
            self.show_warning(self.t("error.add_target"), self.t("error.no_document"))
            return
        if not self.ensure_document_editable(self.t("error.add_target")):
            return
        if not self.categories:
            self.show_warning(self.t("error.add_target"), self.t("error.no_categories"))
            return
        if self.current_index is not None and not self.resolve_pending_edit():
            return
        if self.current_index is not None:
            current_mask = self.document.segments[self.current_index].mask
            if current_mask is None or not np.any(current_mask):
                self.show_warning(
                    self.t("error.add_target"), self.t("error.target_empty")
                )
                return
        category = self.categories[0]
        color_id = self.generate_color_id()
        self.document.add_segment(category, color_id)
        self.current_index = len(self.document.segments) - 1
        self.mode = "smart"
        self.set_checked_button(self.mode_group, "smart")
        self.clear_edit_state()
        self.update_mask_quality()
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
        if self.mode == "smart" and not self.smart_edit_allowed():
            self.mode = "query"
            self.set_checked_button(self.mode_group, self.mode)
        self.update_mask_quality()
        self.refresh_table()
        self.update_tool_controls()
        self.refresh_canvas()

    def resolve_pending_edit(self):
        """Ask whether to commit or discard pending target changes."""
        if not self.has_pending_target_edit():
            return True
        answer = QMessageBox.question(
            self,
            self.t("dialog.pending_edit"),
            self.t("dialog.pending_edit_confirm"),
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
        if (
            self.document is None
            or index >= len(self.document.segments)
            or index != self.current_index
        ):
            return
        if not self.document_is_editable():
            return
        category = self.categories_by_name.get(name)
        if category is None:
            return
        segment = self.document.segments[index]
        if segment.category_id == category.id and segment.category_name == category.name:
            return
        snapshot = self.capture_edit_snapshot()
        self.begin_metadata_edit(index)
        self.document.change_segment_category(index, category)
        combo = self.table.cellWidget(index, self.COL_CATEGORY)
        if combo is not None:
            combo.committed_text = category.name
        self.update_metadata_dirty(index)
        self.record_history(snapshot)
        self.resize_segment_table_columns()
        self.refresh_canvas()

    def assign_random_color(self, index):
        """Assign a new random display color to the current segment."""
        if (
            self.document is None
            or index != self.current_index
            or not self.document_is_editable()
        ):
            return
        snapshot = self.capture_edit_snapshot()
        self.begin_metadata_edit(index)
        self.document.change_segment_color(index, self.generate_color_id())
        self.update_metadata_dirty(index)
        self.record_history(snapshot)
        self.refresh_table()
        self.refresh_canvas()

    def delete_segment(self, index):
        """Delete a segment after user confirmation."""
        if self.document is None or index >= len(self.document.segments):
            return
        if not self.ensure_document_editable(self.t("dialog.delete_target")):
            return
        answer = QMessageBox.question(
            self,
            self.t("dialog.delete_target"),
            self.t("dialog.delete_target_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.document.remove_segment(index)
        if self.current_index == index:
            self.current_index = None
            self.mode = "query"
            self.set_checked_button(self.mode_group, self.mode)
            self.clear_edit_state()
        elif self.current_index is not None and self.current_index > index:
            self.current_index -= 1
        self.update_mask_quality()
        self.refresh_table()
        self.refresh_canvas()

    def change_mode(self, button):
        """Switch the active canvas interaction mode."""
        next_mode = button.property("value")
        if next_mode == "smart" and not self.smart_edit_allowed():
            self.set_checked_button(self.mode_group, self.mode)
            return
        if next_mode == "brush" and (
            not self.document_is_editable() or self.current_index is None
        ):
            self.set_checked_button(self.mode_group, self.mode)
            return
        self.mode = next_mode
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

    def smart_edit_allowed(self):
        """Return whether the selected target is new and still uncommitted."""
        if (
            not self.document_is_editable()
            or self.current_index is None
            or not 0 <= self.current_index < len(self.document.segments)
        ):
            return False
        mask = self.document.segments[self.current_index].mask
        return mask is None or not np.any(mask)

    def capture_edit_snapshot(self):
        """Capture the current target-local pending edit state."""
        if (
            self.document is None
            or self.current_index is None
            or not 0 <= self.current_index < len(self.document.segments)
        ):
            return None
        segment = self.document.segments[self.current_index]
        return EditSnapshot(
            edit_mask=None if self.edit_mask is None else self.edit_mask.copy(),
            previous_logits=(
                None if self.previous_logits is None else self.previous_logits.copy()
            ),
            manual_constraints=(
                None
                if self.manual_constraints is None
                else self.manual_constraints.copy()
            ),
            prompt_points=list(self.prompt_points),
            prompt_labels=list(self.prompt_labels),
            edit_dirty=self.edit_dirty,
            metadata_dirty=self.metadata_dirty,
            metadata_snapshot=self.metadata_snapshot,
            document_dirty=self.document.dirty,
            category_id=segment.category_id,
            category_name=segment.category_name,
            color_id=segment.color_id,
        )

    def restore_edit_snapshot(self, snapshot):
        """Restore one target-local pending edit snapshot."""
        if (
            snapshot is None
            or self.document is None
            or self.current_index is None
            or not 0 <= self.current_index < len(self.document.segments)
        ):
            return
        segment = self.document.segments[self.current_index]
        self.edit_mask = (
            None if snapshot.edit_mask is None else snapshot.edit_mask.copy()
        )
        self.previous_logits = (
            None
            if snapshot.previous_logits is None
            else snapshot.previous_logits.copy()
        )
        self.manual_constraints = (
            None
            if snapshot.manual_constraints is None
            else snapshot.manual_constraints.copy()
        )
        self.prompt_points = list(snapshot.prompt_points)
        self.prompt_labels = list(snapshot.prompt_labels)
        self.edit_dirty = snapshot.edit_dirty
        self.metadata_dirty = snapshot.metadata_dirty
        self.metadata_snapshot = snapshot.metadata_snapshot
        segment.category_id = snapshot.category_id
        segment.category_name = snapshot.category_name
        segment.color_id = snapshot.color_id
        self.document.dirty = snapshot.document_dirty
        self.update_mask_quality()
        self.refresh_table()
        self.update_tool_controls()
        self.update_history_controls()
        self.refresh_canvas()

    def record_history(self, snapshot):
        """Record the state preceding one completed target edit."""
        if snapshot is None:
            return
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.history_limit:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self.update_history_controls()

    def update_history_controls(self):
        """Enable undo and redo only when the current edit session has history."""
        if not hasattr(self, "undo_button"):
            return
        editable = self.document_is_editable() and self.current_index is not None
        self.undo_button.setEnabled(editable and bool(self.undo_stack))
        self.redo_button.setEnabled(editable and bool(self.redo_stack))

    def undo_edit(self):
        """Undo one operation in the current uncommitted target edit session."""
        if not self.undo_stack:
            return
        current = self.capture_edit_snapshot()
        snapshot = self.undo_stack.pop()
        if current is not None:
            self.redo_stack.append(current)
        self.restore_edit_snapshot(snapshot)

    def redo_edit(self):
        """Redo one operation in the current uncommitted target edit session."""
        if not self.redo_stack:
            return
        current = self.capture_edit_snapshot()
        snapshot = self.redo_stack.pop()
        if current is not None:
            self.undo_stack.append(current)
        self.restore_edit_snapshot(snapshot)

    def update_tool_controls(self):
        """Enable editing controls that apply to the current mode."""
        editable = self.document_is_editable()
        selected = self.current_index is not None
        if hasattr(self, "mode_group"):
            for button in self.mode_group.buttons():
                value = button.property("value")
                if value == "query":
                    enabled = True
                elif value == "smart":
                    enabled = self.smart_edit_allowed()
                else:
                    enabled = editable and selected
                button.setEnabled(enabled)
        manual = self.mode == "brush" and editable and selected
        if hasattr(self, "manual_controls"):
            for control in self.manual_controls:
                control.setEnabled(manual)
        if hasattr(self, "canvas"):
            if not manual:
                self.canvas.clear_brush_cursor()
            cursor = {
                "brush": Qt.CrossCursor,
                "smart": Qt.UpArrowCursor,
                "query": Qt.WhatsThisCursor,
            }[self.mode]
            self.canvas.setCursor(cursor)

    def ensure_edit_mask(self):
        """Initialize the editable mask for the selected segment."""
        if not self.ensure_document_editable(self.t("error.edit_target")):
            return False
        if self.document is None or self.current_index is None:
            self.show_warning(self.t("error.edit_target"), self.t("error.no_target"))
            return False
        if self.edit_mask is None:
            segment_mask = self.document.segments[self.current_index].mask
            self.edit_mask = (
                segment_mask.copy()
                if segment_mask is not None
                else np.zeros(self.document.image_rgb.shape[:2], dtype=np.uint8)
            )
        if self.manual_constraints is None and self.smart_edit_allowed():
            self.manual_constraints = np.zeros(
                self.document.image_rgb.shape[:2],
                dtype=np.int8,
            )
        return True

    def ensure_document_editable(self, title):
        """Show the read-only reason before rejecting a mutation."""
        if self.document_is_editable():
            return True
        if self.document is not None and self.document.read_only_reason:
            self.show_warning(title, self.document.read_only_reason)
        return False

    def validate_active_configuration(self):
        """Verify the active configuration still matches the bound document."""
        try:
            data = self.category_manager.load_data(self.active_category_config_id)
        except CategoryConfigError as error:
            self.document.read_only_reason = self.t(
                "readonly.config_invalid", error=error
            )
        else:
            if (
                data.content_hash != self.active_category_config_sha256
                or self.document.category_config_uuid != self.active_category_config_id
                or self.document.category_config_sha256 != data.content_hash
            ):
                self.document.read_only_reason = self.t("readonly.hash_mismatch")
        if not self.document.read_only_reason:
            return True
        self.mode = "query"
        self.set_checked_button(self.mode_group, self.mode)
        self.update_editing_state()
        self.refresh_table()
        self.refresh_canvas()
        self.show_warning(self.t("readonly.title"), self.document.read_only_reason)
        return False

    def clear_edit_state(self):
        """Clear pending mask, metadata, and smart prompt state."""
        self.edit_mask = None
        self.edit_dirty = False
        self.metadata_dirty = False
        self.metadata_snapshot = None
        self.prompt_points = []
        self.prompt_labels = []
        self.previous_logits = None
        self.manual_constraints = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._brush_snapshot = None
        self._brush_position = None
        self._brush_preview_base = None
        self.mask_quality = MaskQuality()
        self.update_history_controls()

    def toggle_quality_check(self, _checked=False):
        """Toggle visual quality hints for the active mask."""
        self.quality_check_enabled = not self.quality_check_enabled
        self.settings.setValue(self.QUALITY_SETTING_KEY, self.quality_check_enabled)
        self.settings.sync()
        self.quality_button.setText(
            self.t("main.quality.on" if self.quality_check_enabled else "main.quality.off")
        )
        self.quality_button.set_active(self.quality_check_enabled)
        self.update_mask_quality()
        self.refresh_canvas()

    def current_quality_mask(self):
        """Return the pending or committed mask for the selected target."""
        if self.document is None or self.current_index is None:
            return None
        if not 0 <= self.current_index < len(self.document.segments):
            return None
        if self.edit_mask is not None:
            return self.edit_mask
        return self.document.segments[self.current_index].mask

    def update_mask_quality(self):
        """Refresh cached quality details for the selected target."""
        self.mask_quality = MaskQuality()
        quality_mask = self.current_quality_mask()
        if self.quality_check_enabled and quality_mask is not None:
            primary_point = next(
                (
                    point
                    for point, label in zip(self.prompt_points, self.prompt_labels)
                    if label == 1
                ),
                None,
            )
            self.mask_quality = inspect_mask_quality(quality_mask, primary_point)
        self.update_quality_overlay()

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
        self.update_mask_quality()
        self.refresh_table()
        self.refresh_canvas()

    def commit_current_segment(self):
        """Commit pending mask and metadata changes for the selected segment."""
        if self.document is None:
            self.show_warning(self.t("error.commit_target"), self.t("error.no_document"))
            return False
        if not self.ensure_document_editable(self.t("error.commit_target")):
            return False
        if self.current_index is None:
            self.show_warning(self.t("error.commit_target"), self.t("error.no_target"))
            return False
        if self.edit_mask is None and not self.metadata_dirty:
            self.show_warning(self.t("error.commit_target"), self.t("error.no_edit"))
            return False
        segment = self.document.segments[self.current_index]
        pending_mask = self.edit_mask if self.edit_mask is not None else segment.mask
        if pending_mask is None or not np.any(pending_mask):
            self.show_warning(self.t("error.commit_target"), self.t("error.no_mask"))
            return False
        if self.edit_mask is not None:
            self.document.commit_mask(
                self.current_index,
                self.edit_mask,
            )
        self.clear_edit_state()
        if self.mode == "smart":
            self.mode = "query"
            self.set_checked_button(self.mode_group, self.mode)
        self.update_mask_quality()
        self.refresh_table()
        self.update_tool_controls()
        self.refresh_canvas()
        self.log(self.t("log.target_committed"))
        return True

    def dilate_edit_mask(self):
        """Dilate the pending binary mask by one iteration."""
        snapshot = self.capture_edit_snapshot()
        if not self.ensure_edit_mask():
            return
        before = self.edit_mask.copy()
        after = cv2.dilate(before, self.morph_kernel, iterations=1)
        changed = before != after
        if not np.any(changed):
            self.restore_edit_snapshot(snapshot)
            return
        self.edit_mask = after
        if self.manual_constraints is not None:
            self.manual_constraints[changed] = 1
        self.edit_dirty = True
        self.record_history(snapshot)
        self.update_mask_quality()
        self.refresh_table()
        self.refresh_canvas()

    def erode_edit_mask(self):
        """Erode the pending binary mask by one iteration."""
        snapshot = self.capture_edit_snapshot()
        if not self.ensure_edit_mask():
            return
        before = self.edit_mask.copy()
        after = cv2.erode(before, self.morph_kernel, iterations=1)
        changed = before != after
        if not np.any(changed):
            self.restore_edit_snapshot(snapshot)
            return
        self.edit_mask = after
        if self.manual_constraints is not None:
            self.manual_constraints[changed] = -1
        self.edit_dirty = True
        self.record_history(snapshot)
        self.update_mask_quality()
        self.refresh_table()
        self.refresh_canvas()

    def save_document(self):
        """Commit pending work and persist the active annotation document."""
        if self.document is None:
            self.show_warning(self.t("error.save"), self.t("error.no_saved_image"))
            return False
        if not self.ensure_document_editable(self.t("error.save")):
            return False
        if not self.validate_active_configuration():
            return False
        if self.has_pending_target_edit() and not self.resolve_pending_edit():
            return False
        empty = [index + 1 for index, segment in enumerate(self.document.segments) if segment.mask is None or not np.any(segment.mask)]
        if empty:
            self.show_warning(
                self.t("error.save"),
                self.t("error.target_without_mask", target=empty),
            )
            return False
        try:
            self.repository.save(self.document)
            self.log(self.t("log.annotation_saved"))
            return True
        except Exception as error:
            self.log_exception(self.t("error.save_annotation"), error)
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
            self.log(self.t("log.embedding_complete", elapsed=elapsed_ms))
            return True
        except Exception as error:
            self.log_exception(self.t("error.embedding"), error)
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def run_smart_prediction(self, x, y, positive):
        """Update the pending mask with a smart positive or negative point."""
        if not self.smart_edit_allowed():
            return
        snapshot = self.capture_edit_snapshot()
        if not self.ensure_edit_mask() or not self.ensure_embedding():
            self.restore_edit_snapshot(snapshot)
            return
        self.prompt_points.append((x, y))
        self.prompt_labels.append(1 if positive else 0)
        try:
            mask_input = build_effective_mask_input(
                self.previous_logits,
                self.manual_constraints,
                model_input_size=self.engine.target_size,
            )
            mask, logits, elapsed_ms = self.engine.predict(
                self.document.embedding,
                self.document.image_rgb.shape[:2],
                self.prompt_points,
                self.prompt_labels,
                mask_input,
            )
            self.edit_mask = apply_manual_constraints(mask, self.manual_constraints)
            self.previous_logits = logits
            self.edit_dirty = True
            self.record_history(snapshot)
            self.update_mask_quality()
            self.refresh_table()
            self.refresh_canvas()
            self.log(self.t("log.segment_complete", elapsed=elapsed_ms))
        except Exception as error:
            self.restore_edit_snapshot(snapshot)
            self.log_exception(self.t("error.segment"), error)

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
                self.log(self.t("log.no_target_at_point"))
            else:
                self.select_segment(index)
            return
        if self.current_index is None:
            self.show_warning(self.t("error.edit_target"), self.t("error.no_target"))
            return
        if self.mode == "smart" and event.button() in {Qt.LeftButton, Qt.RightButton}:
            self.run_smart_prediction(x, y, event.button() == Qt.LeftButton)
            return
        if self.mode == "brush" and event.button() in {Qt.LeftButton, Qt.RightButton}:
            snapshot = self.capture_edit_snapshot()
            if not self.ensure_edit_mask():
                return
            self._brush_snapshot = snapshot
            self._brush_position = None
            self._brush_preview_base = self.document.visible_mask()
            segment = self.document.segments[self.current_index]
            if segment.visible:
                self._brush_preview_base[
                    self._brush_preview_base == segment.color_id
                ] = 0
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
        if position is None:
            self._brush_position = None
            return
        self.paint_at(*position)

    def canvas_mouse_release(self, event):
        """End an active pan or brush stroke."""
        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.pan_origin = None
            self.update_tool_controls()
        snapshot = self._brush_snapshot
        self.painting = None
        self._brush_snapshot = None
        self._brush_position = None
        self._brush_preview_base = None
        if snapshot is not None:
            current = self.capture_edit_snapshot()
            if (
                current is not None
                and (
                    not arrays_equal(snapshot.edit_mask, current.edit_mask)
                    or not arrays_equal(
                        snapshot.manual_constraints,
                        current.manual_constraints,
                    )
                )
            ):
                self.record_history(snapshot)
                self.update_mask_quality()
                self.refresh_table()
                self.refresh_canvas()
            else:
                self.restore_edit_snapshot(snapshot)

    def paint_at(self, x, y):
        """Paint or erase continuously from the previous brush position."""
        end = (x, y)
        start = self._brush_position or end
        radius = self.brush_slider.value()
        paint_brush_segment(self.edit_mask, start, end, radius, self.painting)
        if self.manual_constraints is not None:
            paint_brush_segment(
                self.manual_constraints,
                start,
                end,
                radius,
                1 if self.painting else -1,
            )
        self._brush_position = end
        self.edit_dirty = True
        self.refresh_canvas()

    def canvas_wheel(self, event):
        """Pan with a touchpad and zoom with a mouse wheel or Ctrl-wheel."""
        if self.document is None:
            event.ignore()
            return
        if event.source() == Qt.MouseEventSynthesizedBySystem and not (
            event.modifiers() & Qt.ControlModifier
        ):
            delta = event.pixelDelta()
            if delta.isNull():
                angle = event.angleDelta()
                delta = QPoint(round(angle.x() / 120 * 40), round(angle.y() / 120 * 40))
            horizontal = self.scroll_area.horizontalScrollBar()
            vertical = self.scroll_area.verticalScrollBar()
            horizontal.setValue(horizontal.value() - delta.x())
            vertical.setValue(vertical.value() - delta.y())
            event.accept()
            return
        steps = event.angleDelta().y() / 120.0
        if not steps:
            event.accept()
            return
        self.zoom_canvas(self.zoom_step ** steps, event.pos())
        event.accept()

    def canvas_native_gesture(self, event):
        if event.gestureType() in (Qt.BeginNativeGesture, Qt.EndNativeGesture):
            self.native_zoom_value = None
            return False
        if event.gestureType() != Qt.ZoomNativeGesture or self.document is None:
            return False
        if sys.platform == "win32":
            value = event.value()
            factor = (
                value / self.native_zoom_value
                if self.native_zoom_value and value > 0
                else 1.0
            )
            self.native_zoom_value = value
        else:
            factor = 1.0 + event.value()
        if factor > 0:
            self.zoom_canvas(factor, event.pos())
        event.accept()
        return True

    def zoom_canvas_at_center(self, factor):
        viewport = self.scroll_area.viewport()
        anchor = self.canvas.mapFrom(viewport, viewport.rect().center())
        self.zoom_canvas(factor, anchor)

    def reset_canvas_view(self):
        if self.document is None:
            return
        self.zoom_factor = 1.0
        self.apply_canvas_size()
        self.refresh_canvas()
        self.center_canvas_view()

    def center_canvas_view(self):
        for scrollbar in (
            self.scroll_area.horizontalScrollBar(),
            self.scroll_area.verticalScrollBar(),
        ):
            scrollbar.setValue(scrollbar.maximum() // 2)

    def zoom_canvas(self, factor, anchor):
        if self.document is None or factor <= 0:
            return
        old_width, old_height = self.canvas_size
        viewport_point = self.canvas.mapTo(self.scroll_area.viewport(), anchor)
        x_ratio = anchor.x() / max(1, old_width)
        y_ratio = anchor.y() / max(1, old_height)
        self.zoom_factor = min(
            self.maximum_zoom,
            max(self.minimum_zoom, self.zoom_factor * factor),
        )
        if self.canvas_size == (
            max(1, int(round(self.base_canvas_size[0] * self.zoom_factor))),
            max(1, int(round(self.base_canvas_size[1] * self.zoom_factor))),
        ):
            return
        self.apply_canvas_size()
        self.refresh_canvas()
        new_anchor = QPoint(
            int(round(x_ratio * self.canvas_size[0])),
            int(round(y_ratio * self.canvas_size[1])),
        )
        new_viewport_point = self.canvas.mapTo(self.scroll_area.viewport(), new_anchor)
        horizontal = self.scroll_area.horizontalScrollBar()
        vertical = self.scroll_area.verticalScrollBar()
        horizontal.setValue(horizontal.value() + new_viewport_point.x() - viewport_point.x())
        vertical.setValue(vertical.value() + new_viewport_point.y() - viewport_point.y())

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
        if self.current_index is None or self.edit_mask is None:
            return self.document.visible_mask()
        segment = self.document.segments[self.current_index]
        if self.painting is not None and self._brush_preview_base is not None:
            mask = self._brush_preview_base.copy()
        else:
            mask = self.document.visible_mask()
            if segment.visible:
                mask[mask == segment.color_id] = 0
        if segment.visible:
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
            display[identifier_mask == 0] = self.document.image_rgb[identifier_mask == 0]
        image_height, image_width = self.document.image_rgb.shape[:2]
        native_or_larger = (
            self.canvas_size[0] >= image_width and self.canvas_size[1] >= image_height
        )
        transformation_mode = (
            Qt.FastTransformation
            if self.view_mode == "mask" or native_or_larger
            else Qt.SmoothTransformation
        )
        pixmap = QPixmap.fromImage(qimage_from_rgb(display)).scaled(
            self.canvas_size[0],
            self.canvas_size[1],
            Qt.IgnoreAspectRatio,
            transformation_mode,
        )
        if self.painting is None:
            if self.view_mode == "overlay":
                self.draw_segment_labels(pixmap, identifier_mask)
            if (
                self.quality_check_enabled
                and self.mask_quality.boxes
                and self.current_index is not None
                and self.document.segments[self.current_index].visible
            ):
                self.draw_quality_boxes(pixmap)
            if self.view_mode == "overlay":
                self.draw_prompt_points(pixmap)
        self.canvas.setPixmap(pixmap)

    def draw_quality_boxes(self, pixmap):
        """Draw cached mask quality boxes with a one-pixel red outline."""
        painter = QPainter(pixmap)
        pen = QPen(QColor(255, 0, 0), 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        image_height, image_width = self.document.image_rgb.shape[:2]
        scale_x = pixmap.width() / image_width
        scale_y = pixmap.height() / image_height
        for x, y, width, height in self.mask_quality.boxes:
            left = int(round(x * scale_x))
            top = int(round(y * scale_y))
            right = int(round((x + width) * scale_x))
            bottom = int(round((y + height) * scale_y))
            painter.drawRect(left, top, max(1, right - left), max(1, bottom - top))
        painter.end()

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
        logging.getLogger("parker_label").info(message)

    def show_warning(self, title, message):
        """Show a blocking interaction warning."""
        QMessageBox.warning(self, title, message, QMessageBox.Ok)

    def log_error(self, message):
        """Append an error message to the application log."""
        self.log_area.append(f"<span style='color:#c62828'>{message}</span>")
        logging.getLogger("parker_label").error(message.replace("<br>", "\n"))

    def log_exception(self, context, error):
        """Log an exception with its traceback for diagnosis."""
        QMessageBox.critical(self, context, str(error), QMessageBox.Ok)
        self.log_error(f"{context}：{error}")
        self.log_error(traceback.format_exc().replace("\n", "<br>"))

    def closeEvent(self, event):
        """Resolve unsaved work before closing the application."""
        if self.confirm_document_transition():
            self.shortcut_manager.dispose()
            event.accept()
        else:
            event.ignore()

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .app_info import APP_VERSION, GITEE_RELEASES_URL, GITHUB_RELEASES_URL
from .i18n import language_manager
from .update_checker import UpdateChecker


class UpdateCheckDialog(QDialog):
    def __init__(self, parent, open_url, checker=None):
        super().__init__(parent)
        self.i18n = language_manager
        self.open_url = open_url
        self.checker = checker or UpdateChecker(APP_VERSION)
        self.setWindowTitle(self.t("update.title"))
        self.setMinimumWidth(520)

        self.status_label = QLabel(self.t("update.starting"))
        self.status_label.setWordWrap(True)
        self.version_label = QLabel()
        self.version_label.setWordWrap(True)
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setMinimumHeight(180)
        self.notes.hide()

        self.github_button = QPushButton(self.t("update.open_github"))
        self.gitee_button = QPushButton(self.t("update.open_gitee"))
        self.close_button = QPushButton(self.t("common.close"))
        self.github_button.clicked.connect(lambda: self.open_url(GITHUB_RELEASES_URL))
        self.gitee_button.clicked.connect(lambda: self.open_url(GITEE_RELEASES_URL))
        self.close_button.clicked.connect(self.accept)
        self.github_button.hide()
        self.gitee_button.hide()
        self.close_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.github_button)
        button_layout.addWidget(self.gitee_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.notes)
        layout.addLayout(button_layout)

        self.checker.checking.connect(self.show_checking_source)
        self.checker.completed.connect(self.show_result)
        self.checker.failed.connect(self.show_failure)

    def t(self, key, **values):
        return self.i18n.text(key, **values)

    def start(self):
        return self.checker.start()

    def show_checking_source(self, source):
        source_name = self.t(f"update.source.{source}")
        self.status_label.setText(self.t("update.checking_source", source=source_name))

    def show_result(self, result):
        self.close_button.setEnabled(True)
        if not result.update_available:
            self.status_label.setText(self.t("update.up_to_date"))
            self.version_label.setText(
                self.t("update.current_version", version=result.current_version)
            )
            return
        release = result.release
        self.status_label.setText(self.t("update.available"))
        self.version_label.setText(
            self.t(
                "update.version_summary",
                current=result.current_version,
                latest=release.version,
            )
        )
        self.notes.setPlainText(release.notes or self.t("update.no_notes"))
        self.notes.show()
        self.github_button.show()
        self.gitee_button.show()

    def show_failure(self, error):
        self.status_label.setText(self.t("update.failed"))
        self.version_label.setText(self.t("update.failed_detail", error=error))
        self.close_button.setEnabled(True)

    def reject(self):
        if not self.checker.running:
            super().reject()

    def closeEvent(self, event):
        if self.checker.running:
            event.ignore()
            return
        event.accept()

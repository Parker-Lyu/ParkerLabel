import threading

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from parker_label_app.i18n import language_manager
from parker_label_app.model_manager import (
    DownloadCancelled,
    ensure_models,
    load_manifest,
    manual_download_text,
)
from runtime_paths import model_directory, model_manifest_path


def format_size(value):
    return f"{value / 1024 / 1024:.1f} MiB"


def format_eta(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


class ModelDownloadWorker(QThread):
    sourceChanged = pyqtSignal(str, object)
    progressChanged = pyqtSignal(object, int, int, int, int, float)
    fileComplete = pyqtSignal(object, int, int)
    succeeded = pyqtSignal()
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, manifest, target_directory, parent=None):
        super().__init__(parent)
        self.manifest = manifest
        self.target_directory = target_directory
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    def run(self):
        try:
            ensure_models(
                self.manifest,
                self.target_directory,
                source_changed=self.sourceChanged.emit,
                progress=self.progressChanged.emit,
                file_complete=self.fileComplete.emit,
                cancelled=self._cancelled.is_set,
            )
        except DownloadCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit()


class ModelDownloadDialog(QDialog):
    def __init__(self, manifest, target_directory, parent=None):
        super().__init__(parent)
        self.manifest = manifest
        self.target_directory = target_directory
        self.worker = None
        self.setWindowTitle(language_manager.text("model.title"))
        self.setModal(True)
        self.setMinimumWidth(620)

        self.status_label = QLabel(language_manager.text("model.checking"))
        self.source_label = QLabel()
        self.file_label = QLabel()
        self.size_label = QLabel()
        self.speed_label = QLabel()
        self.eta_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.details_label = QLabel()
        self.details_label.setWordWrap(True)
        self.manual_text = QPlainTextEdit()
        self.manual_text.setReadOnly(True)
        self.manual_text.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.manual_text.setMinimumHeight(175)
        self.manual_text.hide()
        self.download_widgets = (
            self.source_label,
            self.file_label,
            self.size_label,
            self.progress_bar,
            self.speed_label,
            self.eta_label,
        )

        self.cancel_button = QPushButton(language_manager.text("model.cancel"))
        self.retry_button = QPushButton(language_manager.text("model.retry"))
        self.copy_button = QPushButton(language_manager.text("model.copy"))
        self.exit_button = QPushButton(language_manager.text("model.exit"))
        self.retry_button.hide()
        self.copy_button.hide()
        self.exit_button.hide()

        buttons = QDialogButtonBox()
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        buttons.addButton(self.copy_button, QDialogButtonBox.ActionRole)
        buttons.addButton(self.retry_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.exit_button, QDialogButtonBox.RejectRole)

        layout = QVBoxLayout(self)
        for widget in (
            self.status_label,
            self.source_label,
            self.file_label,
            self.size_label,
            self.progress_bar,
            self.speed_label,
            self.eta_label,
            self.details_label,
            self.manual_text,
            buttons,
        ):
            layout.addWidget(widget)

        self.cancel_button.clicked.connect(self.cancel_download)
        self.retry_button.clicked.connect(self.start_download)
        self.copy_button.clicked.connect(self.copy_instructions)
        self.exit_button.clicked.connect(self.reject)
        self.start_download()

    def start_download(self):
        if self.worker and self.worker.isRunning():
            return
        self.status_label.setText(language_manager.text("model.checking"))
        self.source_label.clear()
        self.file_label.clear()
        self.size_label.clear()
        self.speed_label.clear()
        self.eta_label.clear()
        self.details_label.clear()
        self.manual_text.hide()
        for widget in self.download_widgets:
            widget.show()
        self.progress_bar.setValue(0)
        self.cancel_button.show()
        self.cancel_button.setEnabled(True)
        self.retry_button.hide()
        self.copy_button.hide()
        self.exit_button.hide()
        self.adjustSize()
        self.worker = ModelDownloadWorker(self.manifest, self.target_directory, self)
        self.worker.sourceChanged.connect(self.on_source_changed)
        self.worker.progressChanged.connect(self.on_progress)
        self.worker.fileComplete.connect(self.on_file_complete)
        self.worker.succeeded.connect(self.accept)
        self.worker.failed.connect(self.show_failure)
        self.worker.cancelled.connect(self.reject)
        self.worker.start()

    def on_source_changed(self, source, entry):
        self.status_label.setText(language_manager.text("model.downloading"))
        self.source_label.setText(
            language_manager.text("model.source", source="GitHub" if source == "github" else "Gitee")
        )
        self.file_label.setText(
            language_manager.text("model.file", name=entry["path"].split("/", 1)[-1])
        )
        self.size_label.setText(
            language_manager.text("model.file_size", size=format_size(entry["size"]))
        )

    def on_progress(self, entry, downloaded, expected, completed, total, speed):
        overall = completed + downloaded
        self.progress_bar.setValue(round(overall / total * 1000) if total else 1000)
        self.size_label.setText(
            language_manager.text(
                "model.progress",
                current=format_size(downloaded),
                file_size=format_size(expected),
                total_current=format_size(overall),
                total_size=format_size(total),
            )
        )
        if speed > 0:
            self.speed_label.setText(
                language_manager.text("model.speed", speed=f"{speed / 1024:.0f} KiB/s")
            )
            self.eta_label.setText(
                language_manager.text("model.eta", time=format_eta((total - overall) / speed))
            )
        else:
            self.speed_label.setText(language_manager.text("model.measuring"))
            self.eta_label.clear()

    def on_file_complete(self, entry, completed, total):
        self.status_label.setText(language_manager.text("model.verifying"))
        self.progress_bar.setValue(round(completed / total * 1000) if total else 1000)

    def show_failure(self, error):
        self.status_label.setText(language_manager.text("model.failed"))
        self.details_label.setText(
            language_manager.text("model.manual", directory=str(self.target_directory), error=error)
        )
        self.manual_text.setPlainText(manual_download_text(self.manifest, self.target_directory))
        self.manual_text.show()
        for widget in self.download_widgets:
            widget.hide()
        self.cancel_button.hide()
        self.retry_button.show()
        self.copy_button.show()
        self.exit_button.show()
        self.adjustSize()

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.cancel_button.setEnabled(False)
            self.status_label.setText(language_manager.text("model.cancelling"))
            self.worker.cancel()
        else:
            self.reject()

    def copy_instructions(self):
        QGuiApplication.clipboard().setText(self.manual_text.toPlainText())

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(REQUEST_WAIT_MILLISECONDS)
        super().reject()


REQUEST_WAIT_MILLISECONDS = 16000


def ensure_runtime_models(parent=None):
    manifest = load_manifest(model_manifest_path())
    dialog = ModelDownloadDialog(manifest, model_directory(), parent)
    return dialog.exec_() == QDialog.Accepted

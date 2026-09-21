import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication

from parker_label_app.model_download_dialog import ModelDownloadDialog


class ModelDownloadDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_failure_shows_copyable_sources_target_and_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "configs" / "pretrain"
            manifest = {
                "minimum_github_speed_bytes_per_second": 512000,
                "files": [
                    {
                        "path": "pretrain/encoder.onnx",
                        "size": 10,
                        "sha256": "0" * 64,
                        "sources": {
                            "github": "https://github.example/encoder.onnx",
                            "gitee": "https://gitee.example/encoder.onnx",
                        },
                    }
                ],
            }
            with patch.object(ModelDownloadDialog, "start_download") as start:
                dialog = ModelDownloadDialog(manifest, target)
                dialog.show_failure("network unavailable")

                self.assertTrue(dialog.manual_text.isReadOnly())
                self.assertIn("https://github.example/encoder.onnx", dialog.manual_text.toPlainText())
                self.assertIn("https://gitee.example/encoder.onnx", dialog.manual_text.toPlainText())
                self.assertIn(str(target), dialog.manual_text.toPlainText())
                self.assertTrue(dialog.retry_button.isVisibleTo(dialog))
                dialog.retry_button.click()
                self.assertEqual(start.call_count, 2)
                dialog.close()


if __name__ == "__main__":
    unittest.main()

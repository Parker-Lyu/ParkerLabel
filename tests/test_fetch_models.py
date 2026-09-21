import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parker_label_app import model_manager


class ModelManagerTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.payload = b"model-data"
        self.entry = {
            "path": "pretrain/model.onnx",
            "size": len(self.payload),
            "sha256": hashlib.sha256(self.payload).hexdigest(),
            "sources": {"github": "github-url", "gitee": "gitee-url"},
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_valid_existing_model_is_not_downloaded(self):
        destination = self.root / "model.onnx"
        destination.write_bytes(self.payload)
        calls = []

        model_manager.fetch_model(
            self.entry,
            self.root,
            512000,
            downloader=lambda *args: calls.append(args),
        )

        self.assertEqual(calls, [])

    def test_gitee_is_used_when_github_fails(self):
        calls = []

        def downloader(url, target, expected_size, minimum_speed, progress, cancelled):
            calls.append((url, minimum_speed))
            if url == "github-url":
                raise model_manager.DownloadError("slow")
            target.write_bytes(self.payload)

        model_manager.fetch_model(self.entry, self.root, 512000, downloader=downloader)

        self.assertEqual(calls, [("github-url", 512000), ("gitee-url", None)])
        self.assertEqual((self.root / "model.onnx").read_bytes(), self.payload)

    def test_invalid_download_is_rejected_without_replacing_existing_file(self):
        destination = self.root / "model.onnx"
        destination.write_bytes(b"old")

        def downloader(url, target, expected_size, minimum_speed, progress, cancelled):
            target.write_bytes(b"invalid")

        with self.assertRaises(model_manager.DownloadError):
            model_manager.fetch_model(self.entry, self.root, 512000, downloader=downloader)

        self.assertEqual(destination.read_bytes(), b"old")
        self.assertFalse((self.root / ".model.onnx.part").exists())

    def test_only_missing_models_are_downloaded_and_progress_is_aggregated(self):
        valid = dict(self.entry, path="pretrain/valid.onnx")
        (self.root / "valid.onnx").write_bytes(self.payload)
        missing = dict(self.entry, path="pretrain/missing.onnx")
        manifest = {
            "minimum_github_speed_bytes_per_second": 512000,
            "files": [valid, missing],
        }
        progress_events = []

        def downloader(url, target, expected_size, minimum_speed, progress, cancelled):
            target.write_bytes(self.payload)
            progress(len(self.payload), len(self.payload), 1024)

        downloaded = model_manager.ensure_models(
            manifest,
            self.root,
            progress=lambda *values: progress_events.append(values),
            downloader=downloader,
        )

        self.assertEqual(downloaded, [missing])
        self.assertEqual(progress_events[0][3:5], (0, len(self.payload)))

    def test_manual_download_text_lists_both_sources_and_target(self):
        manifest = {"files": [self.entry]}

        text = model_manager.manual_download_text(manifest, self.root)

        self.assertIn(str(self.root), text)
        self.assertIn("GitHub: github-url", text)
        self.assertIn("Gitee: gitee-url", text)

    def test_download_rejects_github_below_the_five_second_speed_threshold(self):
        class Response:
            def __init__(self):
                self.chunks = iter((b"a", b"b", b""))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size):
                return next(self.chunks)

        target = self.root / ".model.onnx.part"
        with patch.object(model_manager.urllib.request, "urlopen", return_value=Response()), patch.object(
            model_manager.time, "monotonic", side_effect=(0.0, 6.0)
        ):
            with self.assertRaises(model_manager.DownloadError):
                model_manager.download_file(
                    "https://github.example/model.onnx",
                    target,
                    2,
                    minimum_speed=512000,
                )


if __name__ == "__main__":
    unittest.main()

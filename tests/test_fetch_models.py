import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fetch_models


class FetchModelsTest(unittest.TestCase):
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
        self.root_patch = mock.patch.object(fetch_models, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temporary_directory.cleanup()

    def test_valid_existing_model_is_not_downloaded(self):
        destination = self.root / self.entry["path"]
        destination.parent.mkdir(parents=True)
        destination.write_bytes(self.payload)
        downloader = mock.Mock()

        fetch_models.fetch_model(self.entry, 512000, downloader)

        downloader.assert_not_called()

    def test_gitee_is_used_when_github_fails(self):
        calls = []

        def downloader(url, target, expected_size, minimum_speed):
            calls.append((url, minimum_speed))
            if url == "github-url":
                raise fetch_models.DownloadError("slow")
            target.write_bytes(self.payload)

        fetch_models.fetch_model(self.entry, 512000, downloader)

        self.assertEqual(calls, [("github-url", 512000), ("gitee-url", None)])
        self.assertEqual((self.root / self.entry["path"]).read_bytes(), self.payload)

    def test_invalid_download_is_rejected(self):
        def downloader(url, target, expected_size, minimum_speed):
            target.write_bytes(b"invalid")

        with self.assertRaises(fetch_models.DownloadError):
            fetch_models.fetch_model(self.entry, 512000, downloader)
        self.assertFalse((self.root / self.entry["path"]).exists())


if __name__ == "__main__":
    unittest.main()

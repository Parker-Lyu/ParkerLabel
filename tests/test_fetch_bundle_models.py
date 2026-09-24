import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from builds.fetch_bundle_models import fetch_models


class BundleModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.payloads = {"encoder.onnx": b"encoder", "decoder.onnx": b"decoder"}
        entries = []
        for name, payload in self.payloads.items():
            entries.append({
                "path": f"pretrain/{name}",
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "sources": {"github": f"https://github.com/example/repo/releases/download/models-v2/{name}"},
            })
        self.manifest = self.root / "model-bundle.json"
        self.manifest.write_text(json.dumps({"files": entries}))

    def tearDown(self):
        self.temporary.cleanup()

    def test_fetches_exact_github_assets_and_reuses_verified_files(self):
        requests = []

        def opener(request, timeout):
            requests.append((request.full_url, timeout))
            return io.BytesIO(self.payloads[request.full_url.rsplit("/", 1)[-1]])

        output = self.root / "generated" / "pretrain"
        paths = fetch_models(self.manifest, output, opener=opener)
        self.assertEqual({path.name for path in paths}, set(self.payloads))
        self.assertEqual(len(requests), 2)
        for path in paths:
            self.assertEqual(path.read_bytes(), self.payloads[path.name])
        fetch_models(self.manifest, output, opener=opener)
        self.assertEqual(len(requests), 2)

    def test_rejects_wrong_hash_without_leaving_partial_model(self):
        output = self.root / "pretrain"
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            fetch_models(self.manifest, output, opener=lambda request, timeout: io.BytesIO(b"x" * 7))
        self.assertFalse((output / "encoder.onnx").exists())
        self.assertFalse((output / ".encoder.onnx.part").exists())


if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from builds import write_build_info


class WriteBuildInfoTests(unittest.TestCase):
    def test_records_candidate_build_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "parker_label_app"
            package.mkdir()
            (package / "app_info.py").write_text(
                'APP_NAME = "ParkerLabel"\nAPP_VERSION = "1.0.0"\n'
            )
            (root / "model-bundle.json").write_text('{"version": "models-v2"}')
            output = root / "build-info.json"
            git_values = {
                ("tag", "--points-at", "HEAD"): "",
                ("status", "--short"): "",
                ("rev-parse", "HEAD"): "abc123",
            }

            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "write_build_info.py",
                        "--project-root",
                        str(root),
                        "--build-type",
                        "candidate",
                        "--output",
                        str(output),
                    ],
                ),
                patch.object(
                    write_build_info,
                    "git_output",
                    side_effect=lambda unused_root, *args: git_values[args],
                ),
                patch.object(
                    write_build_info.importlib.metadata,
                    "version",
                    return_value="test-version",
                ),
            ):
                with patch.object(write_build_info.platform, "system", return_value="Windows"):
                    write_build_info.main()
                self.assertEqual(json.loads(output.read_text())["platform"], "Windows")

                with patch.object(write_build_info.platform, "system", return_value="Darwin"):
                    write_build_info.main()

            info = json.loads(output.read_text())
            self.assertEqual(info["platform"], "macOS")
            self.assertEqual(info["version"], "1.0.0")
            self.assertEqual(info["build_type"], "candidate")
            self.assertIsNone(info["tag"])
            self.assertFalse(info["dirty"])
            self.assertEqual(
                info["model_bundle_sha256"],
                hashlib.sha256((root / "model-bundle.json").read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()

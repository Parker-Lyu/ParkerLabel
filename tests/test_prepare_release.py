import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from builds import prepare_release


class PrepareReleaseTests(unittest.TestCase):
    def test_verifies_tag_version_and_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "parker_label_app"
            package.mkdir()
            (package / "app_info.py").write_text('APP_VERSION = "1.0.0"\n')
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "-qm", "Initial"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "tag", "v1.0.0"], cwd=root, check=True)
            with patch.object(prepare_release, "ROOT", root):
                self.assertEqual(len(prepare_release.verify_tag("v1.0.0")), 40)
                with self.assertRaisesRegex(ValueError, "does not match APP_VERSION"):
                    prepare_release.verify_tag("v1.0.1")

    def make_platform(self, root, name, model_hash, commit):
        source = root / name / "nested"
        source.mkdir(parents=True)
        archive = source / f"ParkerLabel-1.0.0-{name}.zip"
        archive.write_bytes(name.encode())
        system, architecture = prepare_release.PLATFORMS[name]
        (source / "build-info.json").write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "tag": "v1.0.0",
                    "commit": commit,
                    "build_type": "release",
                    "dirty": False,
                    "platform": system,
                    "architecture": architecture,
                    "model_bundle_sha256": model_hash,
                }
            )
        )
        for name_part in ("license-inventory", "size-report"):
            (source / f"{name_part}.json").write_text("{}")
        (source / "SHA256SUMS").write_text(
            f"{prepare_release.sha256(archive)}  {archive.name}\n"
        )
        return source

    def test_stages_unique_assets_and_checksums(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_hash = prepare_release.sha256(prepare_release.ROOT / "model-bundle.json")
            macos = self.make_platform(root, "macos-arm64", model_hash, "a" * 40)
            windows = self.make_platform(root, "windows-x64", model_hash, "a" * 40)
            output = root / "assets"
            with patch.object(prepare_release, "verify_tag", return_value="a" * 40):
                files = prepare_release.stage(
                    "v1.0.0", macos.parent, windows.parent, output
                )
            self.assertEqual(len(files), 8)
            self.assertEqual(len(list(output.glob("*.zip"))), 2)
            self.assertEqual(len(list(output.glob("*.json"))), 6)
            self.assertEqual(len((output / "SHA256SUMS").read_text().splitlines()), 8)
            self.assertIn("Initial release", (output / "release-notes.md").read_text())
            for line in (output / "SHA256SUMS").read_text().splitlines():
                digest, filename = line.split("  ", 1)
                self.assertEqual(digest, prepare_release.sha256(output / filename))

    def test_rejects_platform_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            model_hash = prepare_release.sha256(prepare_release.ROOT / "model-bundle.json")
            macos = self.make_platform(root, "macos-arm64", model_hash, "a" * 40)
            windows = self.make_platform(root, "windows-x64", model_hash, "a" * 40)
            (windows / "SHA256SUMS").write_text("bad checksum\n")
            with patch.object(prepare_release, "verify_tag", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
                    prepare_release.stage(
                        "v1.0.0", macos.parent, windows.parent, root / "assets"
                    )
            self.assertFalse((root / "assets").exists())


if __name__ == "__main__":
    unittest.main()

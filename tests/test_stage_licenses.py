import tempfile
import unittest
from pathlib import Path

from builds.stage_licenses import stage_licenses


class StageLicensesTests(unittest.TestCase):
    def test_stages_only_current_platform_material(self):
        project_root = Path(__file__).resolve().parents[1]
        source = project_root / "third_party_licenses"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "licenses"
            stage_licenses(source, source / "windows-x64-inventory.json", output)
            self.assertTrue((output / "windows-x64-inventory.json").is_file())
            self.assertFalse((output / "macos-arm64-inventory.json").exists())
            self.assertTrue((output / "Qt" / "SOURCE-windows-x64.md").is_file())
            self.assertTrue((output / "Qt" / "attributions-5.15.2").is_dir())
            self.assertFalse((output / "Qt" / "SOURCE.md").exists())
            self.assertFalse((output / "NCurses").exists())
            self.assertTrue((output / "MicrosoftWindowsSDK" / "LICENSE.txt").is_file())


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from builds.audit_windows_licenses import (
    ALWAYS_REQUIRED_LICENSE_FILES,
    REQUIRED_LICENSE_FILES,
    collect_inventory,
    inventory_from_paths,
    validate_archive_licenses,
    validate_licenses,
)


class WindowsLicenseAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "ParkerLabel" / "_internal"

    def tearDown(self):
        self.temporary.cleanup()

    def touch(self, relative_path):
        path = self.runtime / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def test_collects_and_classifies_windows_binaries(self):
        self.touch("PyQt5/QtCore.pyd")
        self.touch("PyQt5/sip.cp311-win_amd64.pyd")
        self.touch("PyQt5/Qt5/bin/Qt5Core.dll")
        self.touch("PyQt5/Qt5/bin/d3dcompiler_47.dll")
        self.touch("PyQt5/Qt5/plugins/platforms/qwindows.dll")
        self.touch("numpy/_core/_multiarray_umath.cp311-win_amd64.pyd")
        self.touch("python311.dll")
        self.touch("vcruntime140.dll")
        inventory = collect_inventory(self.root / "ParkerLabel")
        self.assertEqual(inventory["unknown_dynamic_binaries"], [])
        self.assertEqual(inventory["qt_dlls"], ["Qt5Core.dll"])
        self.assertEqual(inventory["qt_plugins"], ["PyQt5/Qt5/plugins/platforms/qwindows.dll"])
        self.assertEqual(
            {item["name"] for item in inventory["components"]},
            {"MicrosoftDirect3DCompiler", "MicrosoftVisualCRuntime", "NumPy", "PyQt5", "PyQt5_sip", "Python", "Qt"},
        )

    def test_validates_windows_license_files(self):
        licenses = self.root / "licenses"
        (licenses / "THIRD_PARTY_NOTICES.md").parent.mkdir(parents=True)
        (licenses / "THIRD_PARTY_NOTICES.md").touch()
        for filename in ALWAYS_REQUIRED_LICENSE_FILES:
            path = licenses / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        for component in ("MicrosoftVisualCRuntime", "Qt"):
            for filename in REQUIRED_LICENSE_FILES[component]:
                path = licenses / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
        self.assertEqual(validate_licenses(licenses, {"MicrosoftVisualCRuntime", "Qt"}), [])
        (licenses / "Qt" / "REPLACEMENT-windows-x64.md").unlink()
        self.assertEqual(len(validate_licenses(licenses, {"MicrosoftVisualCRuntime", "Qt"})), 1)

    def test_collects_inventory_from_onefile_entries(self):
        inventory = inventory_from_paths(
            {
                "PyQt5/Qt5/bin/Qt5Core.dll",
                "PyQt5/Qt5/plugins/platforms/qwindows.dll",
                "onnxruntime/capi/onnxruntime.dll",
                "onnxruntime/capi/onnxruntime_pybind11_state.pyd",
                "python311.dll",
            }
        )
        self.assertEqual(inventory["unknown_dynamic_binaries"], [])
        self.assertEqual(inventory["qt_dlls"], ["Qt5Core.dll"])
        self.assertEqual(
            {item["name"] for item in inventory["components"]},
            {"ONNXRuntime", "Python", "Qt"},
        )

    def test_validates_embedded_license_entries(self):
        components = {"MicrosoftVisualCRuntime"}
        entries = {"LICENSE"}
        entries.update(
            f"third_party_licenses/{path}"
            for path in (
                "THIRD_PARTY_NOTICES.md",
                *ALWAYS_REQUIRED_LICENSE_FILES,
                *REQUIRED_LICENSE_FILES["MicrosoftVisualCRuntime"],
            )
        )
        self.assertEqual(validate_archive_licenses(entries, components), [])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from builds.audit_macos_licenses import (
    ALWAYS_REQUIRED_LICENSE_FILES,
    REQUIRED_LICENSE_FILES,
    collect_inventory,
    validate_licenses,
)


class MacOSLicenseAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.app = self.root / "ParkerLabel.app"
        self.frameworks = self.app / "Contents" / "Frameworks"
        self.frameworks.mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def touch(self, relative_path):
        path = self.frameworks / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def test_collects_components_and_rejects_unknown_binaries(self):
        self.touch("PyQt5/QtCore.abi3.so")
        self.touch("PyQt5/sip.cpython-311-darwin.so")
        self.touch("PyQt5/Qt5/plugins/platforms/libqcocoa.dylib")
        (self.frameworks / "PyQt5/Qt5/lib/QtCore.framework").mkdir(parents=True)
        self.touch("numpy/_core/_multiarray_umath.cpython-311-darwin.so")
        self.touch("libssl.3.dylib")
        self.touch("unknown.dylib")

        inventory = collect_inventory(self.app)

        self.assertEqual(inventory["qt_frameworks"], ["QtCore"])
        self.assertEqual(inventory["unknown_dynamic_binaries"], ["unknown.dylib"])
        self.assertEqual(
            {item["name"] for item in inventory["components"]},
            {"NumPy", "OpenSSL", "PyQt5", "PyQt5_sip", "Qt"},
        )

    def test_validates_required_license_files(self):
        licenses = self.root / "third_party_licenses"
        (licenses / "THIRD_PARTY_NOTICES.md").parent.mkdir(parents=True)
        (licenses / "THIRD_PARTY_NOTICES.md").touch()
        for filename in ALWAYS_REQUIRED_LICENSE_FILES:
            path = licenses / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        for component in ("PyQt5", "Qt"):
            for filename in REQUIRED_LICENSE_FILES[component]:
                path = licenses / component / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

        self.assertEqual(validate_licenses(licenses, {"PyQt5", "Qt"}), [])
        (licenses / "Qt" / "REPLACEMENT.md").unlink()
        self.assertEqual(len(validate_licenses(licenses, {"PyQt5", "Qt"})), 1)


if __name__ == "__main__":
    unittest.main()

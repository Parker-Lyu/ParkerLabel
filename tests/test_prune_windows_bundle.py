import unittest

from builds.prune_windows_bundle import filtered_toc, should_exclude


class WindowsBundlePruningTests(unittest.TestCase):
    def test_removes_qt_private_msvc_runtime(self):
        self.assertTrue(should_exclude("dbghelp.dll"))
        self.assertFalse(should_exclude("onnxruntime/capi/dbghelp.dll"))
        self.assertTrue(should_exclude("PyQt5/Qt5/bin/MSVCP140.dll"))
        self.assertTrue(should_exclude("PyQt5/Qt5/bin/VCRUNTIME140_1.dll"))
        self.assertTrue(should_exclude("PyQt5/Qt5/plugins/imageformats/qjpeg.dll"))
        self.assertFalse(should_exclude("msvcp140.dll"))

    def test_filters_pyinstaller_binary_toc(self):
        entries = [
            ("PyQt5/Qt5/bin/MSVCP140.dll", "old", "BINARY"),
            ("dbghelp.dll", "windows", "BINARY"),
            ("msvcp140.dll", "current", "BINARY"),
            ("PyQt5/Qt5/bin/Qt5Core.dll", "qt", "BINARY"),
        ]
        self.assertEqual(filtered_toc(entries), entries[2:])


if __name__ == "__main__":
    unittest.main()

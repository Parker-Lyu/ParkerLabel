import unittest
from pathlib import Path

from builds.verify_windows_icon import icon_payloads


class WindowsIconTests(unittest.TestCase):
    def test_windows_icon_contains_required_sizes(self):
        path = (
            Path(__file__).resolve().parent.parent
            / "parker_label_app"
            / "assets"
            / "app-icon.ico"
        )
        data = path.read_bytes()
        payloads = icon_payloads(path)
        sizes = set()
        for index in range(len(payloads)):
            width = data[6 + index * 16] or 256
            height = data[7 + index * 16] or 256
            sizes.add((width, height))
        self.assertEqual(
            sizes,
            {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)},
        )


if __name__ == "__main__":
    unittest.main()

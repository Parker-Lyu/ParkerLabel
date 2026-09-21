#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


VERSIONS = {
    "BZip2": "1.0.8",
    "Expat": "2.8.1",
    "LibFFI": "3.7.0",
    "NCurses": "6.6",
    "NumPy": "2.4.6",
    "ONNXRuntime": "1.29.0",
    "OpenCV": "5.0.0.93",
    "OpenSSL": "3.6.4",
    "PyQt5": "5.15.11",
    "PyQt5_sip": "12.17.1",
    "Python": "3.11.16",
    "Qt": "5.15.18",
    "Readline": "8.3",
    "XZ": "5.8.3",
    "zlib": "1.3.2",
}

REQUIRED_LICENSE_FILES = {
    "BZip2": ["LICENSE"],
    "Expat": ["COPYING"],
    "LibFFI": ["LICENSE"],
    "NCurses": ["COPYING"],
    "NumPy": ["LICENSE.txt"],
    "ONNXRuntime": ["LICENSE", "ThirdPartyNotices.txt"],
    "OpenCV": ["LICENSE.txt", "LICENSE-3RD-PARTY.txt"],
    "OpenSSL": ["LICENSE.txt"],
    "PyQt5": ["LICENSE.GPLv3", "SOURCE.md"],
    "PyQt5_sip": ["LICENSE"],
    "Python": ["LICENSE"],
    "Qt": [
        "LICENSE.LGPL3",
        "SOURCE.md",
        "REPLACEMENT.md",
        "attributions/src/plugins/platforms/cocoa/qt_attribution.json",
    ],
    "Readline": ["COPYING"],
    "XZ": ["COPYING", "COPYING.0BSD"],
    "zlib": ["LICENSE"],
}

ALWAYS_REQUIRED_LICENSE_FILES = [
    "MobileSAM/LICENSE.Apache-2.0",
    "MobileSAM/SOURCE.md",
    "MobileSAM/TINYVIT_LICENSE",
]

RUNTIME_LIBRARY_COMPONENTS = {
    "libbz2.dylib": "BZip2",
    "libcrypto.3.dylib": "OpenSSL",
    "libexpat.1.dylib": "Expat",
    "libffi.8.dylib": "LibFFI",
    "liblzma.5.dylib": "XZ",
    "libncurses.6.dylib": "NCurses",
    "libpython3.11.dylib": "Python",
    "libreadline.8.dylib": "Readline",
    "libssl.3.dylib": "OpenSSL",
    "libtinfo.6.dylib": "NCurses",
    "libz.1.dylib": "zlib",
}


def classify_binary(relative_path):
    path = relative_path.as_posix()
    if path.startswith("PyQt5/Qt5/"):
        return "Qt"
    if path.startswith("PyQt5/"):
        return "PyQt5_sip" if relative_path.name.startswith("sip.") else "PyQt5"
    if path.startswith("numpy/"):
        return "NumPy"
    if path.startswith("cv2/"):
        return "OpenCV"
    if path.startswith("onnxruntime/"):
        return "ONNXRuntime"
    if path.startswith("python3__dot__11/"):
        return "Python"
    return RUNTIME_LIBRARY_COMPONENTS.get(relative_path.name)


def collect_inventory(app_path):
    frameworks_root = app_path / "Contents" / "Frameworks"
    if not frameworks_root.is_dir():
        raise ValueError(f"missing Frameworks directory: {frameworks_root}")

    qt_frameworks = sorted(path.stem for path in frameworks_root.glob("PyQt5/Qt5/lib/*.framework"))
    qt_plugins = sorted(
        path.relative_to(frameworks_root).as_posix()
        for path in frameworks_root.glob("PyQt5/Qt5/plugins/**/*.dylib")
    )
    binaries = sorted(
        path.relative_to(frameworks_root)
        for path in frameworks_root.rglob("*")
        if path.is_file() and path.suffix in {".dylib", ".so"}
    )

    components = {"Qt"} if qt_frameworks or qt_plugins else set()
    unknown = []
    for path in binaries:
        component = classify_binary(path)
        if component is None:
            unknown.append(path.as_posix())
        else:
            components.add(component)

    return {
        "platform": "macos-arm64",
        "components": [
            {"name": name, "version": VERSIONS[name]} for name in sorted(components)
        ],
        "qt_frameworks": qt_frameworks,
        "qt_plugins": qt_plugins,
        "dynamic_binaries": [path.as_posix() for path in binaries],
        "unknown_dynamic_binaries": unknown,
    }


def validate_licenses(licenses_path, component_names):
    errors = []
    notices = licenses_path / "THIRD_PARTY_NOTICES.md"
    if not notices.is_file():
        errors.append(f"missing {notices}")
    for filename in ALWAYS_REQUIRED_LICENSE_FILES:
        path = licenses_path / filename
        if not path.is_file():
            errors.append(f"missing {path}")
    for component in sorted(component_names):
        for filename in REQUIRED_LICENSE_FILES[component]:
            path = licenses_path / component / filename
            if not path.is_file():
                errors.append(f"missing {path}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Audit licenses in a macOS application bundle.")
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--licenses", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    inventory = collect_inventory(args.app)
    errors = []
    if inventory["unknown_dynamic_binaries"]:
        errors.append(
            "unmapped dynamic binaries: "
            + ", ".join(inventory["unknown_dynamic_binaries"])
        )

    if args.expected:
        expected = json.loads(args.expected.read_text(encoding="utf-8"))
        if inventory != expected:
            errors.append("bundle inventory differs from the committed license inventory")

    licenses_path = args.licenses or (
        args.app / "Contents" / "Resources" / "third_party_licenses"
    )
    component_names = {item["name"] for item in inventory["components"]}
    errors.extend(validate_licenses(licenses_path, component_names))
    root_license = args.app / "Contents" / "Resources" / "LICENSE"
    if not root_license.is_file():
        errors.append(f"missing {root_license}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"License audit passed: {len(component_names)} components, "
        f"{len(inventory['dynamic_binaries'])} dynamic binaries"
    )


if __name__ == "__main__":
    main()

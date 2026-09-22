#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


VERSIONS = {
    "BZip2": "1.0.8",
    "Expat": "2.8.1",
    "LibFFI": "3.7.0",
    "MicrosoftDirect3DCompiler": "6.3.9600.16384",
    "MicrosoftUniversalCRT": "10.0.26100.4654",
    "MicrosoftVisualCRuntime": "14.51.36247",
    "NumPy": "2.4.6",
    "ONNXRuntime": "1.29.0",
    "OpenCV": "5.0.0.93",
    "OpenSSL": "3.6.4",
    "PyQt5": "5.15.11",
    "PyQt5_sip": "12.17.1",
    "Python": "3.11.16",
    "Qt": "5.15.2",
    "XZ": "5.8.3",
    "zlib": "1.3.2",
}

REQUIRED_LICENSE_FILES = {
    "BZip2": ["BZip2/LICENSE"],
    "Expat": ["Expat/COPYING"],
    "LibFFI": ["LibFFI/LICENSE"],
    "MicrosoftDirect3DCompiler": ["MicrosoftWindowsSDK/LICENSE.txt"],
    "MicrosoftUniversalCRT": ["MicrosoftWindowsSDK/LICENSE.txt"],
    "MicrosoftVisualCRuntime": ["MicrosoftVisualCRuntime/LICENSE.txt"],
    "NumPy": ["NumPy/LICENSE.txt"],
    "ONNXRuntime": ["ONNXRuntime/LICENSE", "ONNXRuntime/ThirdPartyNotices.txt"],
    "OpenCV": ["OpenCV/LICENSE.txt", "OpenCV/LICENSE-3RD-PARTY.txt"],
    "OpenSSL": ["OpenSSL/LICENSE.txt"],
    "PyQt5": ["PyQt5/LICENSE.GPLv3", "PyQt5/SOURCE.md"],
    "PyQt5_sip": ["PyQt5_sip/LICENSE"],
    "Python": ["Python/LICENSE"],
    "Qt": [
        "Qt/LICENSE.LGPL3",
        "Qt/SOURCE-windows-x64.md",
        "Qt/REPLACEMENT-windows-x64.md",
        "Qt/attributions/src/3rdparty/angle/qt_attribution.json",
        "Qt/attributions-5.15.2/src/3rdparty/libpng/qt_attribution.json",
    ],
    "XZ": ["XZ/COPYING", "XZ/COPYING.0BSD"],
    "zlib": ["zlib/LICENSE"],
}

ALWAYS_REQUIRED_LICENSE_FILES = (
    "OPEN_SOURCE_LICENSES.html",
    "MobileSAM/LICENSE.Apache-2.0",
    "MobileSAM/SOURCE.md",
    "MobileSAM/TINYVIT_LICENSE",
)

RUNTIME_LIBRARY_COMPONENTS = {
    "ffi-8.dll": "LibFFI",
    "libbz2.dll": "BZip2",
    "libcrypto-3-x64.dll": "OpenSSL",
    "libexpat.dll": "Expat",
    "liblzma.dll": "XZ",
    "libssl-3-x64.dll": "OpenSSL",
    "python3.dll": "Python",
    "python311.dll": "Python",
    "zlib.dll": "zlib",
}


def classify_binary(relative_path):
    path = relative_path.as_posix()
    name = relative_path.name.lower()
    if path.startswith("PyQt5/Qt5/"):
        if name == "d3dcompiler_47.dll":
            return "MicrosoftDirect3DCompiler"
        if name.startswith(("msvcp140", "vcruntime140")):
            return "MicrosoftVisualCRuntime"
        return "Qt"
    if path.startswith("PyQt5/"):
        return "PyQt5_sip" if name.startswith("sip.") else "PyQt5"
    if path.startswith(("numpy/", "numpy.libs/")):
        return "NumPy"
    if path.startswith("cv2/"):
        return "OpenCV"
    if path.startswith("onnxruntime/"):
        return "ONNXRuntime"
    if name.startswith("api-ms-win-") or name == "ucrtbase.dll":
        return "MicrosoftUniversalCRT"
    if name.startswith(("msvcp140", "vcruntime140")):
        return "MicrosoftVisualCRuntime"
    if relative_path.parent == Path(".") and relative_path.suffix.lower() == ".pyd":
        return "Python"
    return RUNTIME_LIBRARY_COMPONENTS.get(name)


def inventory_from_paths(paths):
    binaries = sorted(
        Path(str(path).replace("\\", "/"))
        for path in paths
        if Path(str(path)).suffix.lower() in {".dll", ".pyd"}
    )
    components = set()
    unknown = []
    for path in binaries:
        component = classify_binary(path)
        if component is None:
            unknown.append(path.as_posix())
        else:
            components.add(component)
    qt_dlls = sorted(path.name for path in binaries if path.as_posix().startswith("PyQt5/Qt5/bin/Qt5"))
    qt_plugins = sorted(
        path.as_posix()
        for path in binaries
        if path.as_posix().startswith("PyQt5/Qt5/plugins/")
    )
    return {
        "platform": "windows-x64",
        "components": [{"name": name, "version": VERSIONS[name]} for name in sorted(components)],
        "qt_dlls": qt_dlls,
        "qt_plugins": qt_plugins,
        "dynamic_binaries": [path.as_posix() for path in binaries],
        "unknown_dynamic_binaries": unknown,
    }


def collect_inventory(app_path):
    runtime_root = app_path / "_internal"
    if not runtime_root.is_dir():
        raise ValueError(f"missing runtime directory: {runtime_root}")
    return inventory_from_paths(
        path.relative_to(runtime_root)
        for path in runtime_root.rglob("*")
        if path.is_file()
    )


def archive_entries(executable):
    from PyInstaller.archive.readers import CArchiveReader

    return {name.replace("\\", "/") for name in CArchiveReader(str(executable)).toc}


def required_license_paths(component_names):
    paths = {"THIRD_PARTY_NOTICES.md", *ALWAYS_REQUIRED_LICENSE_FILES}
    for component in component_names:
        paths.update(REQUIRED_LICENSE_FILES[component])
    return paths


def validate_licenses(licenses_path, component_names):
    errors = []
    for filename in sorted(required_license_paths(component_names)):
        path = licenses_path / filename
        if not path.is_file():
            errors.append(f"missing {path}")
    return errors


def validate_archive_licenses(entries, component_names):
    required = {f"third_party_licenses/{path}" for path in required_license_paths(component_names)}
    return [f"missing embedded {path}" for path in sorted(required - entries)]


def main():
    parser = argparse.ArgumentParser(description="Audit licenses in a Windows portable bundle.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--app", type=Path)
    source.add_argument("--executable", type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--licenses", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    entries = archive_entries(args.executable) if args.executable else None
    inventory = inventory_from_paths(entries) if entries is not None else collect_inventory(args.app)
    errors = []
    if inventory["unknown_dynamic_binaries"]:
        errors.append("unmapped dynamic binaries: " + ", ".join(inventory["unknown_dynamic_binaries"]))
    if args.expected:
        expected = json.loads(args.expected.read_text(encoding="utf-8"))
        if inventory != expected:
            errors.append("bundle inventory differs from the committed license inventory")
    component_names = {item["name"] for item in inventory["components"]}
    if entries is not None:
        errors.extend(validate_archive_licenses(entries, component_names))
        if "LICENSE" not in entries:
            errors.append("missing embedded LICENSE")
    else:
        licenses_path = args.licenses or args.app / "_internal" / "third_party_licenses"
        errors.extend(validate_licenses(licenses_path, component_names))
        root_license = args.app / "_internal" / "LICENSE"
        if not root_license.is_file():
            errors.append(f"missing {root_license}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"License audit passed: {len(component_names)} components, {len(inventory['dynamic_binaries'])} dynamic binaries")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path


COMPONENT_DIRECTORIES = {
    "MicrosoftDirect3DCompiler": "MicrosoftWindowsSDK",
    "MicrosoftUniversalCRT": "MicrosoftWindowsSDK",
    "MicrosoftVisualCRuntime": "MicrosoftVisualCRuntime",
}


def copy_path(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def stage_licenses(source, inventory_path, output):
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    platform = inventory["platform"]
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for relative_path in (
        "OPEN_SOURCE_LICENSES.html",
        "THIRD_PARTY_NOTICES.md",
        "MobileSAM",
    ):
        copy_path(source / relative_path, output / relative_path)
    copy_path(inventory_path, output / f"{platform}-inventory.json")

    component_names = {item["name"] for item in inventory["components"]}
    directories = {
        COMPONENT_DIRECTORIES.get(component, component)
        for component in component_names
        if component != "Qt"
    }
    for directory in sorted(directories):
        copy_path(source / directory, output / directory)

    qt_source = source / "Qt"
    qt_output = output / "Qt"
    for filename in ("LICENSE.GPL3", "LICENSE.GPL3-EXCEPT", "LICENSE.LGPL3"):
        copy_path(qt_source / filename, qt_output / filename)
    copy_path(qt_source / "attributions", qt_output / "attributions")
    if platform == "macos-arm64":
        copy_path(qt_source / "SOURCE.md", qt_output / "SOURCE.md")
        copy_path(qt_source / "REPLACEMENT-macos-arm64.md", qt_output / "REPLACEMENT-macos-arm64.md")
    elif platform == "windows-x64":
        copy_path(qt_source / "SOURCE-windows-x64.md", qt_output / "SOURCE-windows-x64.md")
        copy_path(qt_source / "REPLACEMENT-windows-x64.md", qt_output / "REPLACEMENT-windows-x64.md")
        copy_path(qt_source / "attributions-5.15.2", qt_output / "attributions-5.15.2")
    else:
        raise ValueError(f"unsupported platform: {platform}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage_licenses(args.source, args.inventory, args.output)


if __name__ == "__main__":
    main()

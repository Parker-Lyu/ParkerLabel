#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path


BYTES_PER_MB = 1_000_000


def tree_size(path):
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        return path.stat().st_size
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and not item.is_symlink()
    )


def measurement(byte_count):
    return {"bytes": byte_count, "mb": round(byte_count / BYTES_PER_MB, 3)}


def component_sizes(app):
    if app.is_file():
        return {"single_executable": measurement(app.stat().st_size)}
    if (app / "Contents" / "Frameworks").is_dir():
        runtime_root = app / "Contents" / "Frameworks"
        roots = {
            "python_runtime": (runtime_root / "libpython3.11.dylib", runtime_root / "python3__dot__11"),
            "qt": (runtime_root / "PyQt5",),
            "opencv": (runtime_root / "cv2",),
            "onnxruntime": (runtime_root / "onnxruntime",),
            "numpy": (runtime_root / "numpy",),
        }
    else:
        runtime_root = app / "_internal"
        roots = {
            "python_runtime": (runtime_root / "python311.dll", runtime_root / "base_library.zip"),
            "qt": (runtime_root / "PyQt5",),
            "opencv": (runtime_root / "cv2",),
            "onnxruntime": (runtime_root / "onnxruntime",),
            "numpy": (runtime_root / "numpy", runtime_root / "numpy.libs"),
        }
    measured = {name: sum(tree_size(path) for path in paths) for name, paths in roots.items()}
    components = {
        name: measurement(size)
        for name, size in sorted(measured.items(), key=lambda item: item[1], reverse=True)
    }
    other_bytes = tree_size(app) - sum(measured.values())
    components["application_and_other"] = measurement(other_bytes)
    return components


def largest_files(app, limit=20):
    if app.is_file():
        return [{"path": app.name, **measurement(app.stat().st_size)}]
    files = (
        item
        for item in app.rglob("*")
        if item.is_file() and not item.is_symlink()
    )
    return [
        {
            "path": str(path.relative_to(app)),
            **measurement(path.stat().st_size),
        }
        for path in sorted(files, key=lambda item: item.stat().st_size, reverse=True)[:limit]
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--configs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    model_bytes = sum(item["size"] for item in manifest["files"])
    app_bytes = tree_size(args.app)
    configs_bytes = tree_size(args.configs)
    model_paths = [args.configs / item["path"] for item in manifest["files"]]
    first_launch_complete = all(path.is_file() for path in model_paths)
    report = {
        "unit": "MB = 1,000,000 bytes",
        "download_archive": measurement(args.archive.stat().st_size),
        "unpacked_application": measurement(app_bytes),
        "model_bundle": measurement(model_bytes),
        "first_launch_complete": first_launch_complete,
        "first_launch_total": (
            measurement(app_bytes + configs_bytes) if first_launch_complete else None
        ),
        "projected_first_launch_total": measurement(app_bytes + model_bytes),
        "first_launch_configs": measurement(configs_bytes),
        "components": component_sizes(args.app),
        "largest_files": largest_files(args.app),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

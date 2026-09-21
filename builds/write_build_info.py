#!/usr/bin/env python3
import argparse
import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEPENDENCIES = (
    "PyInstaller",
    "PyQt5",
    "PyQt5-Qt5",
    "numpy",
    "onnxruntime",
    "opencv-python-headless",
)


def git_output(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    namespace = {}
    exec((root / "parker_label_app" / "app_info.py").read_text(), namespace)
    manifest = json.loads((root / "model-bundle.json").read_text())
    tag = git_output(root, "tag", "--points-at", "HEAD") or None
    dirty = bool(git_output(root, "status", "--short"))
    info = {
        "application": namespace["APP_NAME"],
        "version": namespace["APP_VERSION"] or "dev",
        "tag": tag,
        "commit": git_output(root, "rev-parse", "HEAD"),
        "dirty": dirty,
        "platform": "macOS",
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "dependencies": {
            name: importlib.metadata.version(name) for name in DEPENDENCIES
        },
        "model_bundle": manifest,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


PLATFORMS = {
    "macos-arm64": ("macOS", "arm64"),
    "windows-x64": ("Windows", "AMD64"),
}
METADATA = ("build-info", "license-inventory", "size-report")
TAG_PATTERN = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z")
ROOT = Path(__file__).resolve().parent.parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version():
    namespace = {}
    exec((ROOT / "parker_label_app" / "app_info.py").read_text(), namespace)
    return namespace["APP_VERSION"]


def verify_version():
    current = version()
    if not TAG_PATTERN.fullmatch(f"v{current}"):
        raise ValueError(f"Invalid APP_VERSION: {current!r}")
    return current


def verify_tag(tag):
    if not TAG_PATTERN.fullmatch(tag) or tag != f"v{verify_version()}":
        raise ValueError(f"Tag {tag!r} does not match APP_VERSION")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tagged_commit = subprocess.check_output(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    if tagged_commit != commit:
        raise ValueError(f"Tag {tag} does not point to HEAD")
    return commit


def check_platform(source, platform_name, tag, commit, model_hash):
    archive = source / f"ParkerLabel-{tag[1:]}-{platform_name}.zip"
    info = json.loads((source / "build-info.json").read_text())
    expected_os, expected_arch = PLATFORMS[platform_name]
    expected = {
        "version": tag[1:],
        "tag": tag,
        "commit": commit,
        "build_type": "release",
        "dirty": False,
        "platform": expected_os,
        "architecture": expected_arch,
        "model_bundle_sha256": model_hash,
    }
    for key, value in expected.items():
        if info.get(key) != value:
            raise ValueError(f"{platform_name} build-info {key}: expected {value!r}, got {info.get(key)!r}")
    checksum = (source / "SHA256SUMS").read_text().splitlines()
    if checksum != [f"{sha256(archive)}  {archive.name}"]:
        raise ValueError(f"{platform_name} SHA256SUMS does not match its ZIP")
    for name in METADATA:
        json.loads((source / f"{name}.json").read_text())
    return archive


def locate_source(directory):
    matches = list(directory.rglob("build-info.json"))
    if len(matches) != 1:
        raise ValueError(f"Expected one build-info.json under {directory}, found {len(matches)}")
    return matches[0].parent


def release_notes(tag):
    changelog = (ROOT / "CHANGELOG.md").read_text()
    match = re.search(
        rf"^## {re.escape(tag[1:])}(?:[ \t]+[^\n]*)?\n(.*?)(?=^## |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if not match or not match.group(1).strip():
        raise ValueError(f"CHANGELOG.md has no notes for {tag}")
    return match.group(1).strip() + "\n"


def stage(tag, macos, windows, output):
    commit = verify_tag(tag)
    model_hash = sha256(ROOT / "model-bundle.json")
    sources = {}
    if macos is not None:
        sources["macos-arm64"] = locate_source(macos)
    if windows is not None:
        sources["windows-x64"] = locate_source(windows)
    if not sources:
        raise ValueError("At least one platform artifact is required")
    archives = {
        name: check_platform(source, name, tag, commit, model_hash)
        for name, source in sources.items()
    }
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for platform_name, source in sources.items():
        shutil.copy2(archives[platform_name], output / archives[platform_name].name)
        for name in METADATA:
            shutil.copy2(
                source / f"{name}.json", output / f"{name}-{platform_name}.json"
            )
    files = sorted(output.iterdir())
    (output / "SHA256SUMS").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in files)
    )
    (output / "release-notes.md").write_text(release_notes(tag))
    return files


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-version")
    check = subparsers.add_parser("verify-tag")
    check.add_argument("--tag", required=True)
    prepare = subparsers.add_parser("stage")
    prepare.add_argument("--tag", required=True)
    prepare.add_argument("--macos", type=Path)
    prepare.add_argument("--windows", type=Path)
    prepare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "verify-version":
        verify_version()
    elif args.command == "verify-tag":
        verify_tag(args.tag)
    else:
        stage(args.tag, args.macos, args.windows, args.output)


if __name__ == "__main__":
    main()

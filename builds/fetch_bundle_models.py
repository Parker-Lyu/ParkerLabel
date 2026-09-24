#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


CHUNK_SIZE = 256 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_models(manifest_path, destination, opener=urllib.request.urlopen):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["files"]
    if {entry["path"] for entry in entries} != {
        "pretrain/encoder.onnx", "pretrain/decoder.onnx"
    }:
        raise ValueError("Expected encoder.onnx and decoder.onnx in the model manifest")
    destination.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        filename = Path(entry["path"]).name
        target = destination / filename
        if target.is_file() and target.stat().st_size == entry["size"] and sha256(target) == entry["sha256"]:
            continue
        url = entry["sources"]["github"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "github.com" or "/releases/download/" not in parsed.path:
            raise ValueError(f"Expected a GitHub Release URL for {filename}")
        temporary = destination / f".{filename}.part"
        temporary.unlink(missing_ok=True)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ParkerLabel-builder"})
            with opener(request, timeout=30) as response, temporary.open("wb") as output:
                size = 0
                for chunk in iter(lambda: response.read(CHUNK_SIZE), b""):
                    size += len(chunk)
                    if size > entry["size"]:
                        raise ValueError(f"{filename} exceeds the expected size")
                    output.write(chunk)
            if size != entry["size"] or sha256(temporary) != entry["sha256"]:
                raise ValueError(f"{filename} size or SHA-256 mismatch")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return [destination / Path(entry["path"]).name for entry in entries]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in fetch_models(args.manifest, args.output):
        print(f"Verified bundled model: {path}")


if __name__ == "__main__":
    main()

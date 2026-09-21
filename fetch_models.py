import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "model-bundle.json"
CHUNK_SIZE = 1024 * 1024
SPEED_CHECK_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 15


class DownloadError(RuntimeError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_valid(path, entry):
    return (
        path.is_file()
        and path.stat().st_size == entry["size"]
        and sha256(path) == entry["sha256"]
    )


def download_file(url, target, expected_size, minimum_speed=None):
    request = urllib.request.Request(url, headers={"User-Agent": "ParkerLabel-model-fetcher"})
    started = time.monotonic()
    downloaded = 0
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        with target.open("wb") as output:
            while chunk := response.read(CHUNK_SIZE):
                output.write(chunk)
                downloaded += len(chunk)
                elapsed = time.monotonic() - started
                if minimum_speed and elapsed >= SPEED_CHECK_SECONDS:
                    speed = downloaded / elapsed
                    if speed < minimum_speed:
                        raise DownloadError(
                            f"download speed {speed / 1024:.0f} KB/s is below "
                            f"{minimum_speed / 1024:.0f} KB/s"
                        )
                percent = min(downloaded / expected_size * 100, 100)
                print(f"\r  {percent:5.1f}% ({downloaded / 1024 / 1024:.1f} MiB)", end="", flush=True)
    print()
    if downloaded != expected_size:
        raise DownloadError(f"expected {expected_size} bytes, received {downloaded}")


def fetch_model(entry, minimum_github_speed, downloader=download_file):
    destination = ROOT / entry["path"]
    if is_valid(destination, entry):
        print(f"Verified {entry['path']}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    errors = []
    for source_name in ("github", "gitee"):
        temporary.unlink(missing_ok=True)
        print(f"Downloading {entry['path']} from {source_name}...")
        try:
            minimum_speed = minimum_github_speed if source_name == "github" else None
            downloader(entry["sources"][source_name], temporary, entry["size"], minimum_speed)
            if sha256(temporary) != entry["sha256"]:
                raise DownloadError("SHA-256 mismatch")
            os.replace(temporary, destination)
            print(f"Verified {entry['path']}")
            return
        except Exception as error:
            errors.append(f"{source_name}: {error}")
            print(f"  {source_name} failed: {error}")
    temporary.unlink(missing_ok=True)
    raise DownloadError(f"Could not download {entry['path']}: {'; '.join(errors)}")


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    minimum_speed = manifest["minimum_github_speed_bytes_per_second"]
    failures = []
    for entry in manifest["files"]:
        try:
            fetch_model(entry, minimum_speed)
        except DownloadError as error:
            failures.append(str(error))
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Model bundle {manifest['version']} is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

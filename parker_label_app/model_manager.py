import hashlib
import json
import os
import time
import urllib.request


CHUNK_SIZE = 256 * 1024
SPEED_CHECK_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 15


class DownloadError(RuntimeError):
    pass


class DownloadCancelled(DownloadError):
    pass


def load_manifest(path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def missing_models(manifest, target_directory):
    return [
        entry
        for entry in manifest["files"]
        if not is_valid(target_directory / entry["path"].split("/", 1)[-1], entry)
    ]


def download_file(
    url,
    target,
    expected_size,
    minimum_speed=None,
    progress=None,
    cancelled=None,
):
    request = urllib.request.Request(url, headers={"User-Agent": "ParkerLabel-model-fetcher"})
    downloaded = 0
    first_byte_at = None
    samples = []
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        with target.open("wb") as output:
            while chunk := response.read(CHUNK_SIZE):
                if cancelled and cancelled():
                    raise DownloadCancelled("download cancelled")
                now = time.monotonic()
                if first_byte_at is None:
                    first_byte_at = now
                output.write(chunk)
                downloaded += len(chunk)
                samples.append((now, downloaded))
                cutoff = now - SPEED_CHECK_SECONDS
                while len(samples) > 1 and samples[1][0] <= cutoff:
                    samples.pop(0)
                elapsed = now - first_byte_at
                window_elapsed = now - samples[0][0]
                speed = (
                    (downloaded - samples[0][1]) / window_elapsed
                    if window_elapsed > 0
                    else 0
                )
                if minimum_speed and elapsed >= SPEED_CHECK_SECONDS and speed < minimum_speed:
                    raise DownloadError(
                        f"download speed {speed / 1024:.0f} KiB/s is below "
                        f"{minimum_speed / 1024:.0f} KiB/s"
                    )
                if progress:
                    progress(downloaded, expected_size, speed)
    if downloaded != expected_size:
        raise DownloadError(f"expected {expected_size} bytes, received {downloaded}")


def fetch_model(
    entry,
    target_directory,
    minimum_github_speed,
    downloader=download_file,
    source_changed=None,
    progress=None,
    cancelled=None,
):
    destination = target_directory / entry["path"].split("/", 1)[-1]
    if is_valid(destination, entry):
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    errors = []
    for source_name in ("github", "gitee"):
        if cancelled and cancelled():
            raise DownloadCancelled("download cancelled")
        temporary.unlink(missing_ok=True)
        if source_changed:
            source_changed(source_name, entry)
        try:
            minimum_speed = minimum_github_speed if source_name == "github" else None
            downloader(
                entry["sources"][source_name],
                temporary,
                entry["size"],
                minimum_speed,
                progress,
                cancelled,
            )
            if sha256(temporary) != entry["sha256"]:
                raise DownloadError("SHA-256 mismatch")
            os.replace(temporary, destination)
            return
        except DownloadCancelled:
            temporary.unlink(missing_ok=True)
            raise
        except Exception as error:
            errors.append(f"{source_name}: {error}")
    temporary.unlink(missing_ok=True)
    raise DownloadError(f"Could not download {entry['path']}: {'; '.join(errors)}")


def ensure_models(
    manifest,
    target_directory,
    source_changed=None,
    progress=None,
    file_complete=None,
    cancelled=None,
    downloader=download_file,
):
    entries = missing_models(manifest, target_directory)
    total_size = sum(entry["size"] for entry in entries)
    completed_size = 0
    for entry in entries:
        def report(downloaded, expected_size, speed):
            if progress:
                progress(entry, downloaded, expected_size, completed_size, total_size, speed)

        fetch_model(
            entry,
            target_directory,
            manifest["minimum_github_speed_bytes_per_second"],
            downloader=downloader,
            source_changed=source_changed,
            progress=report,
            cancelled=cancelled,
        )
        completed_size += entry["size"]
        if file_complete:
            file_complete(entry, completed_size, total_size)
    return entries


def manual_download_text(manifest, target_directory):
    lines = [str(target_directory), ""]
    for entry in manifest["files"]:
        filename = entry["path"].split("/", 1)[-1]
        lines.extend(
            [
                filename,
                f"GitHub: {entry['sources']['github']}",
                f"Gitee: {entry['sources']['gitee']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()

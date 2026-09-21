import sys
from pathlib import Path

from parker_label_app.model_manager import (
    DownloadError,
    ensure_models,
    load_manifest,
    manual_download_text,
)


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "model-bundle.json"


def main():
    manifest = load_manifest(MANIFEST_PATH)
    target_directory = ROOT / "pretrain"

    def source_changed(source, entry):
        print(f"Downloading {entry['path']} from {source}...")

    def progress(entry, downloaded, expected, completed, total, speed):
        percent = min((completed + downloaded) / total * 100, 100) if total else 100
        print(
            f"\r  {percent:5.1f}% ({completed + downloaded:.0f}/{total:.0f} bytes)",
            end="",
            flush=True,
        )

    try:
        downloaded = ensure_models(
            manifest,
            target_directory,
            source_changed=source_changed,
            progress=progress,
        )
    except DownloadError as error:
        print(f"\nAutomatic model download failed: {error}", file=sys.stderr)
        print(
            "\nDownload the weights from either the GitHub or Gitee Release link below, "
            "then place the files in the listed directory:",
            file=sys.stderr,
        )
        print(manual_download_text(manifest, target_directory), file=sys.stderr)
        print("\nRun `python fetch_models.py` again to verify the files.", file=sys.stderr)
        return 1
    if downloaded:
        print()
    print(f"Model bundle {manifest['version']} is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import sys
from pathlib import Path

from parker_label_app.model_manager import DownloadError, ensure_models, load_manifest


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "model-bundle.json"


def main():
    manifest = load_manifest(MANIFEST_PATH)

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
            ROOT / "pretrain",
            source_changed=source_changed,
            progress=progress,
        )
    except DownloadError as error:
        print(f"\n{error}", file=sys.stderr)
        return 1
    if downloaded:
        print()
    print(f"Model bundle {manifest['version']} is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Portable build SOP

All reported sizes use `1 MB = 1,000,000 bytes`.

## macOS arm64

Run from an Apple Silicon Mac:

```bash
./builds/build-macos.sh
```

To validate a versioned candidate before creating the release tag, set
`APP_VERSION`, commit the release changes, and run from a clean checkout:

```bash
./builds/build-macos.sh --candidate
```

Candidate artifacts are written under
`builds/output/<version>-candidate/macos-arm64/`, use `-candidate` in the ZIP
name, and record `"build_type": "candidate"` in `build-info.json`. The
application version remains `<version>`.

The script creates a dedicated Miniforge environment at
`builds/.env-macos-arm64/`, builds only the arm64 application, strips eligible
binaries, applies an ad-hoc signature, and writes outputs under
`builds/output/<version>/macos-arm64/`.

The macOS build uses a custom `opencv-python-headless` 5.0.0.93 wheel compiled
from pinned OpenCV 5.0.0 source. The requested modules are `core`, `imgproc`,
`imgcodecs`, and Python bindings; OpenCV 5 also adds their required `geometry`
and `flann` dependencies. JPEG, PNG, and BMP remain supported; video I/O,
FFmpeg, highgui, OpenEXR, OCR, DNN, and unused image codecs are disabled. The
wheel is cached under `builds/.opencv-wheelhouse/`. Delete that directory to
force a clean OpenCV rebuild.

Each build verifies the wheel archive, the exact OpenCV module set and required
image operations, and all project unit tests. After packaging, it verifies the
finished bundle's dynamic-library inventory and bundled license material, then
verifies the ad-hoc signature on both the generated application and a fresh
extraction of the ZIP, tests the ZIP contents, and verifies `SHA256SUMS`.

The output directory contains:

- `ParkerLabel.app`
- `ParkerLabel-<version>-macos-arm64.zip`
- `build-info.json`
- `license-inventory.json`
- `size-report.json`
- `SHA256SUMS`

The runtime models are not bundled. On first launch they are downloaded into
`configs/pretrain/` beside `ParkerLabel.app`. Re-run the size report after the
first successful launch:

```bash
builds/.env-macos-arm64/bin/python builds/measure_bundle.py \
  --app builds/output/dev/macos-arm64/ParkerLabel.app \
  --archive builds/output/dev/macos-arm64/ParkerLabel-dev-macos-arm64.zip \
  --manifest model-bundle.json \
  --configs builds/output/dev/macos-arm64/configs \
  --output builds/output/dev/macos-arm64/size-report.json
```

After validating the candidate, create the `v<version>` tag on the same commit
and run `./builds/build-macos.sh` without `--candidate` for the release build.
The release mode rejects a dirty checkout or a tag that does not exactly match
the application version. Development, candidate, and release builds record
their mode in `build-info.json`.

The application is locally ad-hoc signed. This verifies bundle integrity but
does not identify an Apple developer and is not notarization. Gatekeeper may
reject its command-line assessment and may require the user to open the
application through Finder's Open action or approve it in Privacy & Security.
Do not instruct users to disable Gatekeeper globally.

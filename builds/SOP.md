# Portable build SOP

All reported sizes use `1 MB = 1,000,000 bytes`.

## GitHub draft release

Commit the release-ready source, set `APP_VERSION` to the intended version, and
put that version's notes in `CHANGELOG.md`. Push the source commit to GitHub,
then push its matching `v<version>` tag. The tag push runs
`.github/workflows/release.yml` on GitHub-hosted macOS arm64 and Windows x64
runners. The workflow requires both platform builds and their checks to pass
before it creates a draft GitHub Release. It never publishes the draft.

The draft contains the two platform ZIPs, separate `build-info-<platform>.json`,
`license-inventory-<platform>.json`, and `size-report-<platform>.json` files,
and one `SHA256SUMS` covering all eight other assets. Each ZIP retains its
embedded `build-info.json`. The workflow verifies the platform checksums,
version, tag, commit, build type, and model manifest SHA-256 before upload.
Rerunning the workflow updates an existing draft; it refuses to modify an
already published Release. The release notes come from the matching
`CHANGELOG.md` section.

Download and test the draft packages on their native platforms, including real
inference, saving and reopening annotations, model download and offline use,
Chinese paths, native UI, and preservation of `configs/` during upgrade. After
acceptance, publish the GitHub draft manually. Upload the same assets to Gitee
separately and verify their checksums there. A pushed tag is public even while
the application Release remains a draft.

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

The ZIP contains a top-level `ParkerLabel-<version>/` directory with
`ParkerLabel.app` inside it. Runtime-created `configs/` data therefore stays
inside this directory after extraction.

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

## Windows x64

Run from 64-bit Windows with Miniforge. Visual Studio 2022 Build Tools with the
**Desktop development with C++** workload is preferred; when it is unavailable,
the script uses the pinned Miniforge GCC toolchain. For a tagged release, run:

```powershell
.\builds\build-windows.ps1
```

Git Bash users can run the equivalent shell entry:

```bash
./builds/build-windows.sh
```

To validate a versioned clean commit before creating its release tag, use
`-Candidate` in PowerShell:

```powershell
.\builds\build-windows.ps1 -Candidate
```

Or use `--candidate` in Git Bash:

```bash
./builds/build-windows.sh --candidate
```

As on macOS, candidate builds require `APP_VERSION` and a clean worktree but
do not require a tag. Release builds require the matching `v<version>` tag.

The script creates dedicated environments under `builds/.env-windows-x64/`
and `builds/.env-opencv-windows-x64/`. It builds the pinned OpenCV source as a
headless static wheel containing only `core`, `imgproc`, `imgcodecs`, Python
bindings, and the OpenCV-required `geometry` and `flann` modules. JPEG, PNG and
BMP remain available; video I/O, FFmpeg, MSMF, highgui, OpenEXR, DNN and unused
codecs are disabled. The cached wheel is under `builds/.opencv-wheelhouse/`.

The build runs the OpenCV runtime verifier and all project tests before
packaging. It removes unused Qt DLLs and plugins and Qt's obsolete private MSVC
runtime copies before creating a single executable. It then runs the packaged
Qt/OpenCV/NumPy/ONNX Runtime self-test, audits every embedded `.dll` and `.pyd`
against `third_party_licenses/windows-x64-inventory.json`, validates embedded
license material, tests a fresh ZIP extraction, and verifies `SHA256SUMS`.

Outputs are written under `builds/output/<version>/windows-x64/`:

- `ParkerLabel.exe`
- `configs/`
- `ParkerLabel-<version>-windows-x64.zip`
- `build-info.json`
- `license-inventory.json`
- `size-report.json`
- `SHA256SUMS`

The ZIP contains `ParkerLabel-<version>/ParkerLabel.exe` and an empty
`ParkerLabel-<version>/configs/` directory. Users extract the ZIP and run the
single `ParkerLabel.exe`; its packaged
dependencies are extracted to a temporary runtime directory automatically.
Python, Conda and project dependencies are not required. Models and user
configuration are stored in `configs/` beside the executable. Preserve that
directory when replacing the executable during an upgrade. Windows SmartScreen
or antivirus software may still show a security prompt for unsigned builds.

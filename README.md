# Parker Label

Parker Label is a lightweight, interactive annotation tool powered by MobileSAM. It is designed for creating object-detection bounding boxes and instance-segmentation masks without requiring a discrete GPU. On an Apple M5 Pro, an interactive mask-decoder inference takes approximately 20 ms; initial image embedding is measured separately.

## Run

Install a Conda distribution if you do not already have one. [Miniforge](https://github.com/conda-forge/miniforge) is recommended, but other Conda distributions also work. Open a terminal, then clone the repository, create a Python 3.11 environment, and install the dependencies:

```bash
git clone https://github.com/Parker-Lyu/ParkerLabel.git
cd ParkerLabel
conda create -n parker-label -c conda-forge python=3.11 onnxruntime=1.29.1 -y
conda activate parker-label
python -m pip install -r requirements.txt
python fetch_models.py
```

`fetch_models.py` downloads `encoder.onnx` and `decoder.onnx` into `pretrain/`. It prefers GitHub when the measured download speed is at least 500 KiB/s, falls back to Gitee, and verifies file size and SHA-256. Then start the app from the repository root with the environment active:

```bash
python main.py
```

Packaged builds do not include the ONNX files. On startup, ParkerLabel verifies the files in `configs/pretrain/` beside the program and downloads missing or invalid files from GitHub, falling back to Gitee when GitHub is unavailable or slower than 500 KiB/s. If both sources fail, the dialog shows copyable release URLs and the exact destination directory for manual installation.

Use **Settings → Interface Language** to select 中文（简体）, 中文（繁體）, English, 日本語, 한국어, Deutsch, Français, Italiano, or Español. The selection is saved for the next launch. **Settings → Tooltips** controls contextual hints.

Use **Settings → Keyboard Shortcuts** to view, change, clear, or restore key bindings. **Help → About ParkerLabel** shows application information. Smart, Manual, and Inspect modes use `Q`, `W`, and `E` by default. Edited bindings take effect when saved and persist across launches.

## Categories

The application bundles `config/default-coco.json` as the read-only set of 80 COCO detection categories. User category files are stored in `configs/categories/` beside the program. Use the **类别配置** button to add, delete, disable, or rename categories.

Portable settings, including the startup category selection, are stored in `configs/settings.ini`. The application log is `configs/app.log`; it is cleared on each launch and limited to two 1 MB files while the app runs. Keep the program in a writable directory so it can create `configs/`.

## Annotation files

Each source image uses three neighboring artifact files:

- `.npy` stores the reusable image embedding.
- `.json` stores per-instance category, bounding box, area, and uncompressed COCO RLE at source-image resolution.
- `.mask.png` stores a flattened color preview at source-image resolution. When instances overlap, later instances appear on top. The JSON instance masks remain authoritative.

The per-image JSON uses COCO annotation fields but is not a complete COCO dataset file. A complete COCO dataset export requires top-level `images`, `annotations`, and `categories` arrays in one dataset JSON.

### JSON fields

- `format` identifies the local annotation schema.
- `image` records the image identifier, file name, width, and height.
- `annotations` contains one record per instance.
- `id` is the instance identifier within the image file.
- `image_id` links the instance to the image record.
- `category_id` references the active category configuration.
- `category_name` keeps the readable category name.
- `color_id` controls the display and preview color.
- `bbox` stores `[x, y, width, height]` in source-image pixels.
- `area` stores the instance pixel area at source-image resolution.
- `iscrowd` follows the COCO crowd flag convention.
- `segmentation` stores the independent instance mask as uncompressed COCO RLE.

## Modules

- `main.py` creates the Qt application and opens the main window.
- `runtime_paths.py` locates bundled resources and portable data paths, and initializes logging.
- `parker_label_app/window.py` coordinates the desktop interface and annotation workflow.
- `parker_label_app/canvas.py` renders the interactive canvas and forwards pointer, wheel, and drop events.
- `parker_label_app/models.py` defines categories, segments, documents, and independent instance masks.
- `parker_label_app/editing.py` handles brush strokes, manual mask constraints, and edit snapshots.
- `parker_label_app/inference.py` loads and runs the ONNX encoder and decoder.
- `parker_label_app/annotation_io.py` loads images, annotations, and embeddings, then saves annotation files, embeddings, and mask previews.
- `parker_label_app/image_utils.py` handles image loading, resizing, mask colors, and Qt image conversion.
- `parker_label_app/quality.py` detects disconnected mask regions and enclosed holes.
- `parker_label_app/category_store.py` validates and persists versioned category configurations.
- `parker_label_app/category_dialog.py` provides category editing in the interface.
- `parker_label_app/shortcuts.py` manages platform key bindings and persistence; `parker_label_app/shortcut_dialog.py` provides the editor.
- `parker_label_app/app_info.py` holds application identity and project links.
- `parker_label_app/locales/` contains JSON translations for all nine interface languages; `parker_label_app/i18n.py` loads them and persists the selected language.
- `mobile_sam/` contains the MobileSAM model source and ONNX export scripts; normal annotation uses the exported ONNX files.

## Regenerate ONNX models

**Dependencies:** Install `torch` and `torchvision` using the [PyTorch instructions for your platform](https://pytorch.org/get-started/locally/), then run `python -m pip install timm onnx onnxruntime`. Verified versions: torch 2.13.0, torchvision 0.28.0, timm 1.0.19, onnx 1.22.0, and onnxruntime 1.29.1.

**Checkpoint:** Create `pretrain/`, then download the official [MobileSAM `mobile_sam.pt`](https://github.com/ChaoningZhang/MobileSAM/blob/master/weights/mobile_sam.pt) to `pretrain/mobile_sam.pt`. It is the only weight needed for both exports; no separate TinyViT or SAM checkpoint is required.

**Export:** From the repository root, run:

```bash
python -m mobile_sam.export_mobilesam_encoder --checkpoint pretrain/mobile_sam.pt --output pretrain/encoder.onnx
python -m mobile_sam.export_mobilesam_decoder --checkpoint pretrain/mobile_sam.pt --model-type vit_t --output pretrain/decoder.onnx
```

The application runs the resulting ONNX files. `mobile_sam.pt` and the export dependencies are not needed at runtime. Model files in `pretrain/` are excluded from Git.

## Licenses

Parker Label's original code, including `mobile_sam/export_mobilesam_encoder.py`, is licensed under [GPL-3.0-only](LICENSE).

The third-party code in `mobile_sam/` retains its own licenses: [MobileSAM](https://github.com/ChaoningZhang/MobileSAM) and [Segment Anything](https://github.com/facebookresearch/segment-anything) use Apache License 2.0, and the TinyViT code carries a Microsoft MIT notice. See [`mobile_sam/LICENSE`](mobile_sam/LICENSE), [`mobile_sam/TINYVIT_LICENSE`](mobile_sam/TINYVIT_LICENSE), and [`mobile_sam/THIRD_PARTY.md`](mobile_sam/THIRD_PARTY.md) for the license texts and attribution.

The GUI uses PyQt5 and Qt under their own licenses. See [Riverbank's PyQt licensing](https://www.riverbankcomputing.com/software/pyqt), [Qt's open-source obligations](https://www.qt.io/development/open-source-lgpl-obligations), and the [release license plan](docs/release-licenses.md).

# Parker Label

Parker Label is a lightweight, interactive annotation tool powered by MobileSAM. It is designed for creating object-detection bounding boxes and instance-segmentation masks without requiring a discrete GPU. On an Apple M5 Pro, an interactive mask-decoder inference takes approximately 20 ms; initial image embedding is measured separately.

## Run

```bash
conda activate parker-label
python main.py
```

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

- `main.py` starts the application.
- `parker_label_app/window.py` coordinates the desktop interface and annotation workflow.
- `runtime_paths.py` locates bundled resources and portable user data.
- `parker_label_app/canvas.py` renders the interactive canvas and forwards pointer, wheel, and drop events.
- `parker_label_app/models.py` owns annotation state and independent instance masks.
- `parker_label_app/inference.py` runs the ONNX encoder and decoder.
- `parker_label_app/annotation_io.py` loads and saves annotation artifacts.
- `parker_label_app/image_utils.py` handles image loading, resizing, mask colors, and Qt image conversion.
- `parker_label_app/quality.py` detects disconnected mask regions and enclosed holes.
- `parker_label_app/category_store.py` validates and persists category configurations.
- `parker_label_app/category_dialog.py` provides category editing in the interface.
- `parker_label_app/shortcuts.py` manages platform key bindings and persistence; `shortcut_dialog.py` provides the editor.
- `parker_label_app/app_info.py` holds application identity and project links.
- `parker_label_app/locales/` contains JSON translations for all nine interface languages; `parker_label_app/i18n.py` loads them and persists the selected language.
- `mobile_sam/` contains the MobileSAM model implementation and ONNX export scripts.

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

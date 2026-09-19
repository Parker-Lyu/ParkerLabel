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

The application reads `config/default-coco.json`. The default configuration contains the 80 COCO detection categories. Use the **类别配置** button to add, delete, disable, or rename categories.

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
- `category_id` references `config/default-coco.json`.
- `category_name` keeps the readable category name.
- `color_id` controls the display and preview color.
- `bbox` stores `[x, y, width, height]` in source-image pixels.
- `area` stores the instance pixel area at source-image resolution.
- `iscrowd` follows the COCO crowd flag convention.
- `segmentation` stores the independent instance mask as uncompressed COCO RLE.

## Modules

- `main.py` starts the application.
- `parker_label_app/window.py` coordinates the desktop interface and annotation workflow.
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
- `export_mobilesam_encoder.py` and `export_mobilesam_decoder.py` regenerate the ONNX deployment models.
- `mobile_sam/` contains the MobileSAM model implementation used by the export scripts.

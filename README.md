# Parker Label

Parker Label is a desktop tool for object detection and instance segmentation annotation. Each instance owns an independent binary mask, and its bounding box is calculated from that mask.

## Run

```bash
conda activate parker-label
python main.py
```

## Categories

The application reads `config/categories.json`. The default configuration contains the 80 COCO detection categories. Use the **类别配置** button to add, delete, disable, rename, or recolor categories.

## Annotation files

Each source image uses neighboring artifact files:

- `.npy` stores the reusable image embedding.
- `.json` stores per-instance category, bounding box, area, and uncompressed COCO RLE at source-image resolution.
- `.mask.png` stores a flattened color preview for compatibility. The JSON RLE remains authoritative because a single color image cannot preserve overlapping instances.

## Modules

- `main.py` starts the application.
- `parker_label_app/window.py` coordinates the desktop interface.
- `parker_label_app/models.py` owns annotation state and independent instance masks.
- `parker_label_app/inference.py` runs the ONNX encoder and decoder.
- `parker_label_app/annotation_io.py` loads and saves annotation artifacts.
- `parker_label_app/category_store.py` validates and persists category configuration.
- `parker_label_app/category_dialog.py` provides category editing in the interface.
- `parker_label_app/validation.py` checks empty and noisy instance masks.

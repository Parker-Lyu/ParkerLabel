# Changelog

## Unreleased

## 1.0.0 - 2026-10-01

Initial release of ParkerLabel.

### Annotation

- Add CPU-based, MobileSAM-assisted annotation with AI, Manual, and Inspect modes. Positive and negative clicks guide AI masks; overlay view preserves the brightness of unlabeled image areas.
- Save per-image instance annotations with category, bounding box, area, and COCO RLE masks, alongside an image embedding cache and mask preview.
- Include the 80-category COCO configuration and versioned, immutable custom category configurations with integrity checks when reopening annotations.

### Interface

- Provide nine interface languages, configurable keyboard shortcuts, and persistent settings.
- Group canvas controls for zoom, Image/Mask/Overlay views, AI prompt-point visibility, quality checks, and editing into a single toolbar row with sharp icons on high DPI displays.
- Show localized image-opening and drag-and-drop guidance, the current Open Image shortcut, and up to five recent images with valid paths on the empty canvas. Clicking the central icon opens the image picker.
- Simplify Help navigation and About information, with offline access to third-party licenses.
- Add manual update checks with GitHub queries, Gitee fallback, and download-page links.

### Portable releases

- Provide portable macOS arm64 and Windows x64 packages with bundled MobileSAM models for offline use, without requiring Python or Conda on the user's computer.
- Store settings, categories, logs, and models in program-adjacent `configs/` so upgrades can preserve them. Resolve the original portable directory under macOS App Translocation, or show instructions to move the extracted folder.
- Build each platform from a matching version tag and collect packages in a draft GitHub Release for manual acceptance, with build metadata, license materials, and SHA-256 checksums.

### Documentation

- Document source setup, category configurations, annotation files, and model export.
- Add an interactive annotation demo and illustrated first-launch guidance for macOS security confirmation and Windows SmartScreen.

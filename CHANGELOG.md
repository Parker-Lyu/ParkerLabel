# Changelog

## Unreleased

## 1.0.0

### Initial release

- Add CPU-based, MobileSAM-assisted image annotation with smart clicks, manual editing, and mask inspection. Overlay view preserves the brightness of unlabeled image areas.
- Save per-image instance annotations with category, bounding box, area, and COCO RLE mask data, alongside an image embedding cache and mask preview.
- Include the 80-category COCO configuration and support versioned, immutable custom category configurations with integrity checks for saved annotations.
- Provide nine interface languages, configurable keyboard shortcuts, and persistent settings.
- Provide portable macOS arm64 and Windows x64 builds, with program-adjacent configuration and verified ONNX model downloads from GitHub or Gitee.
- Build both platforms from a version tag and collect verified assets in a draft GitHub Release for manual acceptance.
- Add manual update checks and offline access to third-party license information.

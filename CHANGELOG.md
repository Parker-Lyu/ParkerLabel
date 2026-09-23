# Changelog

## Unreleased

## 1.0.0 - 2026-09-23

### Application

- Add native Settings and Help menus for language, tooltips, and application information; a compact two-by-two control layout; and configurable keyboard shortcuts with platform defaults, conflict checks, and persistent settings.
- Use English as the default interface language on first launch.
- Add an application icon for source launches and portable builds, with a transparent background that preserves its shadow.
- Add manual background update checks with GitHub-to-Gitee fallback and localized release details.
- Add offline open-source license access from both the Help menu and About dialog, with source and local license-file links.

### Models and packaging

- Publish the reproducible MobileSAM ONNX bundle as `models-v2` with fixed source, tool version, size, and SHA-256 provenance.
- Add a reproducible, size-focused macOS arm64 portable build with a minimal OpenCV runtime and component reports.
- Add the Windows x64 portable build pipeline, minimal OpenCV source build, locked dependencies, native binary and license audit, and Qt DLL replacement documentation.
- Wrap macOS and Windows portable archives in a versioned top-level directory.
- Add a clean-checkout candidate build mode that marks artifacts and build metadata without requiring a release tag.
- Bundle third-party notices for the final package and add a macOS dynamic-library license audit.
- Embed the multi-resolution application icon in the Windows executable and verify it during packaging.

### Fixes

- Allow extra horizontal panning space around zoomed images so their left and right edges can move away from the viewport edges.
- Hide Quality Check boxes for extra mask regions and holes when the selected target's Show setting is off.
- Fix repeated smart-click segmentation by feeding only the selected single-channel low-resolution mask back into MobileSAM.
- Fix mask preview saving for image paths containing Chinese or other Unicode characters on Windows.
- Fix ONNX Runtime initialization in the Windows package by removing the outdated Qt MSVC runtime and switching to a single-executable portable build.

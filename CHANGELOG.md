# Changelog

## Unreleased

- Add the Windows x64 portable build, minimal OpenCV source build, locked
  dependencies, platform-specific native binary/license audit, and Qt DLL
  replacement documentation.

- Use English as the default interface language on first launch.

- Fix repeated smart-click segmentation by feeding only the selected
  single-channel low-resolution mask back into MobileSAM.

- Add an explicit clean-checkout candidate build mode that does not require a
  release tag and marks candidate artifacts and build metadata.

- Add the bundled open-source license page to both the Help menu and About
  dialog, including source and complete local license-file links.

- Publish the reproducible MobileSAM ONNX bundle as `models-v2` with fixed
  source, tool-version, size, and SHA-256 provenance.
- Bundle final-package third-party notices and add a macOS dynamic-library
  license audit plus an offline Help menu entry.

- Add manual background update checks with GitHub-to-Gitee fallback and localized release details.

- Build the macOS arm64 package with a minimal OpenCV runtime.

- Add a reproducible, size-focused macOS arm64 portable build with component reports.

- Add native Settings and Help menus, including interface language, tooltips, and application information.
- Reduce the primary controls to a compact two-by-two layout.
- Add configurable keyboard shortcuts with platform defaults, conflict checks, and persistent settings.

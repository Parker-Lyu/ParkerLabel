# Release license procedure

Parker Label's root `LICENSE` remains GPL-3.0-only. Third-party components keep
their own licenses and notices under `third_party_licenses/`.

The macOS build scans the finished, pruned `.app` with
`builds/audit_macos_licenses.py`. It compares every bundled `.so` and `.dylib`,
the Qt frameworks, and the Qt plugins with
`third_party_licenses/macos-arm64-inventory.json`. A build fails when a binary
is unknown, the inventory changes, or required license material is missing.

The application bundle contains:

```text
Contents/Resources/LICENSE
Contents/Resources/third_party_licenses/THIRD_PARTY_NOTICES.md
Contents/Resources/third_party_licenses/<component>/...
```

`third_party_licenses/THIRD_PARTY_NOTICES.md` is the human-readable component
list. The PyQt5 directory records how to obtain the exact GPL corresponding
source. The Qt directory records the exact LGPL qtbase source revision,
third-party attributions, and instructions for replacing the bundled dynamic
libraries.

For every release:

1. Build on the target platform from the release tag.
2. Run the bundle audit after all pruning and before signing or archiving.
3. Review inventory changes against the actual package and add or remove
   license material accordingly.
4. Keep `license-inventory.json`, `build-info.json`, `size-report.json`, the
   archive, and `SHA256SUMS` with the release artifacts.
5. Repeat the same final-package inventory work independently for Windows. The
   macOS inventory is not evidence for the Windows portable package.

Model source, checkpoint identity, exporter commits, commands, tool versions,
and converted hashes are maintained in `docs/model-provenance.md`.

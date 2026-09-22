# Release license procedure

Parker Label's root `LICENSE` remains GPL-3.0-only. Third-party components keep
their own licenses and notices under `third_party_licenses/`.

The macOS build scans the finished, pruned `.app` with
`builds/audit_macos_licenses.py`; the Windows build scans the PyInstaller
single-executable archive with `builds/audit_windows_licenses.py`. Each compares
every bundled native binary and Qt plugin with its own committed platform
inventory. A build fails when a binary is unknown, the inventory changes, or
required license material is missing.

Each application bundle contains:

```text
Contents/Resources/LICENSE
Contents/Resources/third_party_licenses/OPEN_SOURCE_LICENSES.html
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
5. Audit macOS and Windows independently. One platform's successful inventory
   is not evidence for the other platform.

The two packages share ParkerLabel's root GPL-3.0-only license and byte-identical
third-party license texts. Platform-specific inventories, Qt source and dynamic
library replacement instructions, and Microsoft runtime terms remain separate.

Model source, checkpoint identity, exporter commits, commands, tool versions,
and converted hashes are maintained in `docs/model-provenance.md`.

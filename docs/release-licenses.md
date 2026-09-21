# Release license plan

The current development environment uses PyQt5 5.15.11 and Qt 5.15.15. Check the libraries and licenses in each actual release build before distributing it.

## Repository layout

| Location | Purpose |
| --- | --- |
| `LICENSE` | Parker Label's own license, to be selected by the project owner. With the GPL edition of PyQt5, GPL v3 is the straightforward choice for the complete application. Do not label third-party code as solely owned by Parker Label. |
| `mobile_sam/LICENSE` | Apache License 2.0 for the included MobileSAM and Segment Anything code. |
| `mobile_sam/TINYVIT_LICENSE` | TinyViT's MIT license and upstream third-party notices. |
| `mobile_sam/THIRD_PARTY.md` | Source and file attribution for the included model and exporter code. |
| `third_party_licenses/` | License texts and notices for the exact PyQt5, Qt, and other dependencies that the release build actually contains. Add this directory when the build dependency inventory is fixed. |

The root README should link to this plan and the license files. The release archive or application bundle should include the root license, the applicable third-party license texts and notices, and a clear link to the complete corresponding source and build instructions for that release.

## PyQt5 and Qt packaging

1. Record the PyQt5 and Qt versions, license editions, Qt modules, plugins, and other libraries copied into the finished bundle. A development environment package list is not a substitute for inspecting the bundle.
2. If using the GPL edition of PyQt5, select a compatible license for the complete distributed application and provide its corresponding source. Publishing source on GitHub alone does not select a license.
3. For Qt libraries distributed under the LGPL, include their license and notices, make the corresponding Qt source available as required, and document how recipients can replace the bundled Qt libraries with modified compatible builds and run the application. Validate this with the actual packaged layout on each platform.
4. Include the license texts and notices for any other libraries in the bundle. Copy the release's license directory into the distributed artifact and make it reachable from the README or About dialog.

Licensing references: [Riverbank PyQt licensing](https://www.riverbankcomputing.com/software/pyqt), [Riverbank license FAQ](https://riverbankcomputing.com/commercial/license-faq), and [Qt open-source obligations](https://www.qt.io/development/open-source-lgpl-obligations).

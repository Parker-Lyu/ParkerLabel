# Third-party notices

This directory covers the redistributable components found by scanning the
finished macOS arm64 `ParkerLabel.app`. The machine-readable file
`macos-arm64-inventory.json` records every bundled `.so` and `.dylib`, the Qt
frameworks, and the Qt plugins. The build fails if that inventory changes or a
required license file is absent.

| Component | Version | Bundled evidence | License material |
| --- | --- | --- | --- |
| PyQt5 | 5.15.11 | `PyQt5/QtCore.abi3.so`, `QtGui.abi3.so`, `QtWidgets.abi3.so` | `PyQt5/` |
| PyQt5-sip | 12.17.1 | `PyQt5/sip.cpython-311-darwin.so` | `PyQt5_sip/` |
| Qt | 5.15.18 | QtCore, QtDBus, QtGui, QtPrintSupport and QtWidgets frameworks; Cocoa and macOS style plugins | `Qt/` |
| NumPy | 2.4.6 | Native modules below `numpy/` | `NumPy/` |
| OpenCV | 5.0.0.93 | `cv2/cv2.abi3.so` | `OpenCV/` |
| ONNX Runtime | 1.29.0 | `libonnxruntime.1.29.0.dylib` and Python binding | `ONNXRuntime/` |
| Python | 3.11.16 | `libpython3.11.dylib` and standard-library extension modules | `Python/` |
| OpenSSL | 3.6.4 | `libcrypto.3.dylib`, `libssl.3.dylib` | `OpenSSL/` |
| bzip2 | 1.0.8 | `libbz2.dylib` | `BZip2/` |
| libffi | 3.7.0 | `libffi.8.dylib` | `LibFFI/` |
| Expat | 2.8.1 | `libexpat.1.dylib` | `Expat/` |
| XZ Utils | 5.8.3 | `liblzma.5.dylib` | `XZ/` |
| ncurses | 6.6 | `libncurses.6.dylib`, `libtinfo.6.dylib` | `NCurses/` |
| GNU Readline | 8.3 | `libreadline.8.dylib` | `Readline/` |
| zlib | 1.3.2 | `libz.1.dylib` | `zlib/` |

The application downloads the separately versioned MobileSAM-derived ONNX
models on first use. Their Apache 2.0 license, TinyViT notices, checkpoint
source, and original checkpoint SHA-256 are included in `MobileSAM/`; complete
conversion provenance is maintained in `docs/model-provenance.md`.

OpenCV and ONNX Runtime include their upstream third-party notice files in
their respective directories. The Qt `attributions/` directory preserves the
qtbase attribution manifests and associated license texts. It is intentionally
conservative: an attribution can be present even when a particular optional
qtbase code path is not used by this application.

Apple system frameworks and libraries referenced from `/System/Library` or
`/usr/lib` are provided by macOS and are not copied into the application.
Build-only packages that are absent from the final bundle are not listed as
distributed runtime components.

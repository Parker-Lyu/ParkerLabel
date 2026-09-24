# Third-party notices

This directory covers the redistributable components found by scanning each
finished ParkerLabel package. `macos-arm64-inventory.json` and
`windows-x64-inventory.json` separately record every bundled native binary and
Qt plugin. Each platform build fails if its inventory changes or required
license material is absent. ParkerLabel itself remains GPL-3.0-only on both
platforms under the single root `LICENSE`.

## macOS arm64

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

The application includes the separately versioned MobileSAM-derived ONNX
models. Their Apache 2.0 license, TinyViT notices, checkpoint
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

## Windows x64

| Component | Version | Bundled evidence | License material |
| --- | --- | --- | --- |
| PyQt5 | 5.15.11 | `PyQt5/QtCore.pyd`, `QtGui.pyd`, `QtWidgets.pyd` | `PyQt5/` |
| PyQt5-sip | 12.17.1 | `PyQt5/sip.cp311-win_amd64.pyd` | `PyQt5_sip/` |
| Qt | 5.15.2 | QtCore, QtDBus, QtGui, QtNetwork and QtWidgets DLLs; Windows platform and Vista style plugins; ANGLE and software OpenGL DLLs | `Qt/` |
| NumPy | 2.4.6 | Native modules and libraries below `numpy/` and `numpy.libs/` | `NumPy/` |
| OpenCV | 5.0.0.93 | Minimal static `cv2/cv2.pyd` build | `OpenCV/` |
| ONNX Runtime | 1.29.0 | `onnxruntime.dll`, provider library and Python binding | `ONNXRuntime/` |
| Python | 3.11.16 | `python311.dll` and standard-library extension modules | `Python/` |
| OpenSSL | 3.6.4 | `libcrypto-3-x64.dll`, `libssl-3-x64.dll` | `OpenSSL/` |
| bzip2 | 1.0.8 | `libbz2.dll` | `BZip2/` |
| libffi | 3.7.0 | `ffi-8.dll` | `LibFFI/` |
| Expat | 2.8.1 | `libexpat.dll` | `Expat/` |
| XZ Utils | 5.8.3 | `liblzma.dll` | `XZ/` |
| zlib | 1.3.2 | `zlib.dll` | `zlib/` |
| Microsoft Visual C++ Runtime | 14.51.36247; Qt-bundled 14.26.28720.3 | `msvcp140*.dll`, `vcruntime140*.dll` | `MicrosoftVisualCRuntime/` |
| Microsoft Universal CRT | 10.0.26100.4654 | `ucrtbase.dll`, API-set forwarding DLLs | `MicrosoftWindowsSDK/` |
| Microsoft Direct3D Compiler | 6.3.9600.16384 | Qt's `d3dcompiler_47.dll` | `MicrosoftWindowsSDK/` |

The Windows Qt corresponding-source record and DLL replacement instructions
are `Qt/SOURCE-windows-x64.md` and `Qt/REPLACEMENT-windows-x64.md`. Attribution
texts identical across the two Qt source versions are shared in
`Qt/attributions/`; Qt 5.15.2-specific files are in
`Qt/attributions-5.15.2/`. Windows system DLLs referenced from the operating
system but not copied into the package are not distributed components.

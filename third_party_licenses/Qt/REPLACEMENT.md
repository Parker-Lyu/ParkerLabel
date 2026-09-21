# Replacing the bundled Qt libraries on macOS arm64

Recipients may replace the Qt frameworks and plugins with modified compatible
Qt 5.15.18 arm64 builds. Work on a copy of `ParkerLabel.app` and keep the same
framework names, versioned directory layout, binary install names, and plugin
filenames.

The replaceable locations are:

```text
ParkerLabel.app/Contents/Frameworks/PyQt5/Qt5/lib/*.framework
ParkerLabel.app/Contents/Frameworks/PyQt5/Qt5/plugins/platforms/libqcocoa.dylib
ParkerLabel.app/Contents/Frameworks/PyQt5/Qt5/plugins/styles/libqmacstyle.dylib
```

After replacement, inspect linkage and apply a new local ad-hoc signature:

```bash
find ParkerLabel.app/Contents/Frameworks/PyQt5/Qt5 -type f \
  \( -name '*.dylib' -o -perm -111 \) -exec otool -L {} \;
codesign --force --deep --sign - ParkerLabel.app
codesign --verify --deep --strict --verbose=2 ParkerLabel.app
open ParkerLabel.app
```

The replacement build must remain ABI-compatible with PyQt5 5.15.11. An
ad-hoc signature checks bundle integrity only; it is not Apple notarization or
developer identity verification. Functional validation remains the
recipient's responsibility after replacement.

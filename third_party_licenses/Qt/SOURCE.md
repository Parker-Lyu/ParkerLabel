# Qt corresponding source

The macOS arm64 bundle contains Qt 5.15.18 frameworks and plugins from the
LGPL release of the `qtbase` repository. The exact source baseline is:

- Tag: `v5.15.18-lts-lgpl`
- Commit: `49adb85d34918034e0d6a4c23817407103fb9f73`
- Repository: `https://code.qt.io/qt/qtbase.git`

Obtain and verify it with:

```bash
git clone --branch v5.15.18-lts-lgpl --depth 1 \
  https://code.qt.io/qt/qtbase.git qtbase-5.15.18
git -C qtbase-5.15.18 rev-parse HEAD
```

The result must be the commit above. The bundle scan records these qtbase
components: QtCore, QtDBus, QtGui, QtPrintSupport, QtWidgets,
`plugins/platforms/libqcocoa.dylib`, and `plugins/styles/libqmacstyle.dylib`.

The LGPL v3 text is copied as `LICENSE.LGPL3`. The `attributions/` directory
contains the qtbase third-party attribution manifests and their adjacent
license texts from the same source commit.

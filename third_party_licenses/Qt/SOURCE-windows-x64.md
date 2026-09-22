# Qt corresponding source for Windows x64

The Windows x64 bundle contains Qt 5.15.2 DLLs and plugins from the
`PyQt5_Qt5-5.15.2-py3-none-win_amd64.whl` wheel.

- Wheel SHA-256: `750b78e4dba6bdf1607febedc08738e318ea09e9b10aea9ff0d73073f11f6962`
- Qt tag: `v5.15.2`
- qtbase commit: `40143c189b7c1bf3c2058b77d00ea5c4e3be8b28`
- Repository: `https://code.qt.io/qt/qtbase.git`

Obtain and verify the corresponding source with:

```powershell
git clone --branch v5.15.2 --depth 1 https://code.qt.io/qt/qtbase.git qtbase-5.15.2
git -C qtbase-5.15.2 rev-parse HEAD
```

The result must be the commit above. The Windows bundle scan records QtCore,
QtDBus, QtGui, QtNetwork and QtWidgets DLLs, the Windows platform plugin and
the Windows Vista style plugin.

`attributions/` contains attribution files that are byte-identical between
the macOS Qt 5.15.18 source and this Qt 5.15.2 source.
`attributions-5.15.2/` contains the Qt 5.15.2 files that differ or exist only
in that source release. Together they preserve the qtbase 5.15.2 third-party
attribution manifests and referenced license texts.

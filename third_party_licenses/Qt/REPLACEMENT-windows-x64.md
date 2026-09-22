# Replacing the bundled Qt libraries on Windows x64

Recipients may replace the Qt DLLs and plugins with modified compatible Qt
5.15.2 x64 builds. Work on a copy of the portable `ParkerLabel` directory and
keep the same DLL and plugin filenames.

The replaceable locations are:

```text
ParkerLabel\_internal\PyQt5\Qt5\bin\Qt5*.dll
ParkerLabel\_internal\PyQt5\Qt5\bin\libEGL.dll
ParkerLabel\_internal\PyQt5\Qt5\bin\libGLESv2.dll
ParkerLabel\_internal\PyQt5\Qt5\bin\opengl32sw.dll
ParkerLabel\_internal\PyQt5\Qt5\plugins\platforms\qwindows.dll
ParkerLabel\_internal\PyQt5\Qt5\plugins\styles\qwindowsvistastyle.dll
```

Keep the replacement build ABI-compatible with PyQt5 5.15.11 and ensure all
of its dependent DLLs are present. After replacement, inspect dependencies
with a PE dependency viewer, start `ParkerLabel.exe`, open JPEG and PNG images,
run inference, and exercise file dialogs and the bundled license page.

Functional validation and compliance for replacement libraries remain the
recipient's responsibility.

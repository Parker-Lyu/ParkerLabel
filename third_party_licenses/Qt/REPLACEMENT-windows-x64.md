# Replacing the bundled Qt libraries on Windows x64

Recipients may replace the Qt DLLs and plugins with modified compatible Qt
5.15.2 x64 builds. The DLLs are stored inside the PyInstaller single-file
archive and extracted to a temporary directory when the program starts.

To create a replacement executable:

```powershell
conda create --yes --prefix builds\.env-windows-x64 python=3.11.16 pip=26.0.1
builds\.env-windows-x64\python.exe -m pip install -r builds\requirements-windows-x64.lock
# Replace PyQt5\Qt5\bin and PyQt5\Qt5\plugins in this environment.
.\builds\build-windows.ps1
```

Keep the replacement build ABI-compatible with PyQt5 5.15.11 and ensure all
of its dependent DLLs are present. The build removes Qt's private copies of
MSVCP140 and VCRUNTIME140 so Qt and ONNX Runtime use the current runtime at the
archive root. After rebuilding, inspect dependencies with a PE dependency
viewer, start `ParkerLabel.exe`, open JPEG and PNG images, run inference, and
exercise file dialogs and the bundled license page.

Functional validation and compliance for replacement libraries remain the
recipient's responsibility.

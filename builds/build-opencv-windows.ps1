[CmdletBinding()]
param(
    [string]$TargetPython
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$buildEnv = Join-Path $projectRoot "builds\.env-opencv-windows-x64"
$sourceDir = Join-Path $projectRoot "builds\.opencv-python-src"
$wheelhouse = Join-Path $projectRoot "builds\.opencv-wheelhouse"
$opencvPythonCommit = "b83046cda41133f1bf2e73e99dba16a1248f103a"
$opencvCommit = "40738fb16ceddb5fb3fea747585f7ce6abb0605b"
$wheel = Join-Path $wheelhouse "opencv_python_headless-5.0.0.93-cp37-abi3-win_amd64.whl"

if (-not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) {
    throw "OpenCV must be built from a 64-bit PowerShell process on 64-bit Windows."
}
if (-not $TargetPython) {
    $TargetPython = Join-Path $projectRoot "builds\.env-windows-x64\python.exe"
}
if (-not (Test-Path -LiteralPath $TargetPython -PathType Leaf)) {
    throw "Target Python does not exist: $TargetPython"
}
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "Miniforge/Conda is required."
}

$buildPython = Join-Path $buildEnv "python.exe"
if (-not (Test-Path -LiteralPath $buildPython -PathType Leaf)) {
    & conda create --yes --prefix $buildEnv python=3.11.16 pip=26.0.1
    if ($LASTEXITCODE -ne 0) { throw "Unable to create the OpenCV build environment." }
}
& $buildPython -m pip install --disable-pip-version-check cmake==3.31.10 ninja==1.13.2 numpy==2.0.2 packaging==26.3 scikit-build==0.18.1 setuptools==69.5.1 wheel==0.48.0
if ($LASTEXITCODE -ne 0) { throw "Unable to install OpenCV build dependencies." }

if (-not (Test-Path -LiteralPath $wheel -PathType Leaf)) {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    $vsRoot = $null
    if (Test-Path -LiteralPath $vswhere -PathType Leaf) {
        $vsRoot = (& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath | Select-Object -First 1)
    }
    if ($vsRoot) {
        $devShell = Join-Path $vsRoot "Common7\Tools\Microsoft.VisualStudio.DevShell.dll"
        Import-Module $devShell
        Enter-VsDevShell -VsInstallPath $vsRoot -SkipAutomaticLocation -DevCmdArguments "-arch=x64 -host_arch=x64"
    } else {
        & conda install --yes --prefix $buildEnv gcc_win-64=15.2.0 gxx_win-64=15.2.0
        if ($LASTEXITCODE -ne 0) { throw "Unable to install the Miniforge GCC fallback toolchain." }
        $compilerBin = Join-Path $buildEnv "Library\bin"
        $env:PATH = "$(Join-Path $buildEnv 'Scripts');$compilerBin;$env:PATH"
        $env:CC = Join-Path $compilerBin "x86_64-w64-mingw32-gcc.exe"
        $env:CXX = Join-Path $compilerBin "x86_64-w64-mingw32-g++.exe"
        $env:OPENCV_MINGW = "1"
    }

    $resolvedBuilds = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "builds"))
    $resolvedSource = [System.IO.Path]::GetFullPath($sourceDir)
    if (-not $resolvedSource.StartsWith($resolvedBuilds + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "OpenCV source path escaped the builds directory."
    }
    if (Test-Path -LiteralPath $resolvedSource) {
        Remove-Item -LiteralPath $resolvedSource -Recurse -Force
    }
    & git init $resolvedSource
    & git -C $resolvedSource remote add origin https://github.com/opencv/opencv-python.git
    & git -C $resolvedSource fetch --depth 1 origin $opencvPythonCommit
    & git -C $resolvedSource checkout --detach FETCH_HEAD
    & git -C $resolvedSource submodule update --init --depth 1 opencv
    if ($LASTEXITCODE -ne 0) { throw "Unable to fetch the pinned OpenCV sources." }
    if ((& git -C $resolvedSource rev-parse HEAD) -ne $opencvPythonCommit) {
        throw "Unexpected opencv-python source revision."
    }
    if ((& git -C (Join-Path $resolvedSource "opencv") rev-parse HEAD) -ne $opencvCommit) {
        throw "Unexpected OpenCV source revision."
    }
    & git -C $resolvedSource tag 93
    & git -C $resolvedSource apply --ignore-space-change --ignore-whitespace (Join-Path $projectRoot "builds\opencv-python-minimal.patch")
    if ($LASTEXITCODE -ne 0) { throw "Unable to apply the minimal OpenCV patch." }

    $cmakeArgs = @(
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_LIST=core,imgproc,imgcodecs,python3",
        "-DBUILD_JPEG=ON", "-DBUILD_OPENEXR=OFF", "-DBUILD_PNG=ON", "-DBUILD_ZLIB=ON",
        "-DBUILD_opencv_apps=OFF", "-DBUILD_opencv_java=OFF", "-DBUILD_opencv_js=OFF",
        "-DBUILD_opencv_python_tests=OFF", "-DBUILD_opencv_world=OFF", "-DBUILD_SHARED_LIBS=OFF",
        "-DBUILD_DOCS=OFF", "-DBUILD_EXAMPLES=OFF", "-DBUILD_PERF_TESTS=OFF", "-DBUILD_TESTS=OFF",
        "-DINSTALL_C_EXAMPLES=OFF", "-DINSTALL_PYTHON_EXAMPLES=OFF",
        "-DOPENCV_ENABLE_NONFREE=OFF", "-DOPENCV_GENERATE_PKGCONFIG=OFF",
        "-DWITH_1394=OFF", "-DWITH_ADE=OFF", "-DWITH_AVIF=OFF", "-DWITH_EIGEN=OFF",
        "-DWITH_FFMPEG=OFF", "-DWITH_GDAL=OFF", "-DWITH_GDCM=OFF", "-DWITH_GSTREAMER=OFF",
        "-DWITH_IMGCODEC_HDR=OFF", "-DWITH_IMGCODEC_GIF=OFF", "-DWITH_IMGCODEC_PFM=OFF",
        "-DWITH_IMGCODEC_PXM=OFF", "-DWITH_IMGCODEC_SUNRASTER=OFF", "-DWITH_JASPER=OFF",
        "-DWITH_JPEGXL=OFF", "-DWITH_ITT=OFF", "-DWITH_LAPACK=OFF", "-DWITH_MSMF=OFF",
        "-DWITH_OPENCL=OFF", "-DWITH_OPENEXR=OFF", "-DWITH_OPENJPEG=OFF", "-DWITH_PROTOBUF=OFF",
        "-DWITH_QUIRC=OFF", "-DWITH_TIFF=OFF", "-DWITH_VTK=OFF", "-DWITH_WEBP=OFF"
    )
    if (-not $vsRoot) {
        $env:CFLAGS = "-static-libgcc"
        $env:CXXFLAGS = "-static-libgcc -static-libstdc++"
        $env:LDFLAGS = "-static-libgcc -static-libstdc++ -static -s"
    }
    New-Item -ItemType Directory -Force -Path $wheelhouse | Out-Null
    $env:CMAKE_ARGS = $cmakeArgs -join " "
    $env:CMAKE_GENERATOR = if ($vsRoot) { "Ninja" } else { "Ninja Multi-Config" }
    $env:CMAKE_BUILD_PARALLEL_LEVEL = [Environment]::ProcessorCount.ToString()
    $env:ENABLE_CONTRIB = "0"
    $env:ENABLE_HEADLESS = "1"
    $env:OPENCV_MINIMAL = "1"
    Push-Location $resolvedSource
    try {
        & $buildPython setup.py bdist_wheel --py-limited-api=cp37 --dist-dir $wheelhouse
        if ($LASTEXITCODE -ne 0) { throw "OpenCV wheel build failed." }
    } finally {
        Pop-Location
    }
}

& $TargetPython -m zipfile -t $wheel
if ($LASTEXITCODE -ne 0) { throw "OpenCV wheel archive validation failed." }
& $TargetPython -m pip uninstall --yes opencv-contrib-python opencv-contrib-python-headless opencv-python opencv-python-headless 2>$null | Out-Null
& $TargetPython -m pip install --disable-pip-version-check --force-reinstall --no-deps $wheel
if ($LASTEXITCODE -ne 0) { throw "Unable to install the minimal OpenCV wheel." }

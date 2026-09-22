[CmdletBinding()]
param(
    [switch]$Candidate
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envPrefix = Join-Path $projectRoot "builds\.env-windows-x64"
$generatedDir = Join-Path $projectRoot "builds\.generated"
$workDir = Join-Path $projectRoot "builds\.pyinstaller-work"
$python = Join-Path $envPrefix "python.exe"
$pyinstaller = Join-Path $envPrefix "Scripts\pyinstaller.exe"

if (-not [Environment]::Is64BitOperatingSystem -or -not [Environment]::Is64BitProcess) {
    throw "This build requires 64-bit Windows and 64-bit PowerShell."
}
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "Miniforge/Conda is required."
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    & conda create --yes --prefix $envPrefix python=3.11.16 pip=26.0.1 packaging=26.3 setuptools=84.0.0 wheel=0.48.0
    if ($LASTEXITCODE -ne 0) { throw "Unable to create the Windows build environment." }
}
& $python -m pip install --disable-pip-version-check --requirement (Join-Path $projectRoot "builds\requirements-windows-x64.lock")
if ($LASTEXITCODE -ne 0) { throw "Unable to install the Windows build dependencies." }
& (Join-Path $projectRoot "builds\build-opencv-windows.ps1") -TargetPython $python
& $python (Join-Path $projectRoot "builds\verify_opencv_runtime.py")
if ($LASTEXITCODE -ne 0) { throw "Minimal OpenCV verification failed." }
& $python -m unittest discover --start-directory (Join-Path $projectRoot "tests") --pattern "test_*.py"
if ($LASTEXITCODE -ne 0) { throw "Project tests failed." }

$version = (& $python -c "from parker_label_app.app_info import APP_VERSION; print(APP_VERSION or 'dev')").Trim()
$buildType = "development"
$artifactVersion = $version
$status = (& git -C $projectRoot status --short) -join "`n"
if ($Candidate) {
    if ($version -eq "dev") { throw "Candidate builds require APP_VERSION to be set." }
    if ($status) { throw "Candidate builds require a clean worktree." }
    $buildType = "candidate"
    $artifactVersion = "$version-candidate"
} elseif ($version -ne "dev") {
    if ($status) { throw "Release builds require a clean worktree." }
    $tags = (& git -C $projectRoot tag --points-at HEAD) -join "`n"
    if (($tags -split "`n") -notcontains "v$version") {
        throw "Release builds require HEAD to have tag v$version."
    }
    $buildType = "release"
}

$outputDir = Join-Path $projectRoot "builds\output\$artifactVersion\windows-x64"
$stageDir = Join-Path $workDir "dist"
$executable = Join-Path $outputDir "ParkerLabel.exe"
$configsDir = Join-Path $outputDir "configs"
$packageDir = Join-Path $workDir "package"
$archive = Join-Path $outputDir "ParkerLabel-$artifactVersion-windows-x64.zip"
$buildsRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "builds"))
foreach ($path in @($generatedDir, $workDir)) {
    $resolved = [System.IO.Path]::GetFullPath($path)
    if (-not $resolved.StartsWith($buildsRoot + [System.IO.Path]::DirectorySeparatorChar)) {
        throw "Build path escaped the builds directory: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}
New-Item -ItemType Directory -Force -Path $generatedDir, $workDir, $outputDir | Out-Null
foreach ($path in @($executable, $configsDir, (Join-Path $outputDir "ParkerLabel"))) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
}
foreach ($path in @($archive, (Join-Path $outputDir "build-info.json"), (Join-Path $outputDir "license-inventory.json"), (Join-Path $outputDir "SHA256SUMS"), (Join-Path $outputDir "size-report.json"))) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
}

& $python (Join-Path $projectRoot "builds\write_build_info.py") --project-root $projectRoot --build-type $buildType --output (Join-Path $generatedDir "build-info.json")
if ($LASTEXITCODE -ne 0) { throw "Unable to write build metadata." }
& $python (Join-Path $projectRoot "builds\stage_licenses.py") --source (Join-Path $projectRoot "third_party_licenses") --inventory (Join-Path $projectRoot "third_party_licenses\windows-x64-inventory.json") --output (Join-Path $generatedDir "third_party_licenses")
if ($LASTEXITCODE -ne 0) { throw "Unable to stage Windows license material." }
$env:PARKER_LABEL_VERSION = $version
& $pyinstaller --noconfirm --clean --distpath $stageDir --workpath (Join-Path $workDir "build") (Join-Path $projectRoot "builds\ParkerLabel.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
Move-Item -LiteralPath (Join-Path $stageDir "ParkerLabel.exe") -Destination $executable
& $python (Join-Path $projectRoot "builds\verify_windows_icon.py") --executable $executable --icon (Join-Path $projectRoot "parker_label_app\assets\app-icon.ico")
if ($LASTEXITCODE -ne 0) { throw "Packaged executable icon verification failed." }
New-Item -ItemType Directory -Force -Path $configsDir | Out-Null
$probe = Start-Process -FilePath $executable -ArgumentList "--runtime-self-test" -PassThru -Wait
if ($probe.ExitCode -ne 0) { throw "Packaged Qt/OpenCV/NumPy/ONNX Runtime self-test failed." }
& $python (Join-Path $projectRoot "builds\audit_windows_licenses.py") --executable $executable --expected (Join-Path $projectRoot "third_party_licenses\windows-x64-inventory.json") --report (Join-Path $outputDir "license-inventory.json")
if ($LASTEXITCODE -ne 0) { throw "Windows license audit failed." }

New-Item -ItemType Directory -Force -Path $packageDir, (Join-Path $packageDir "configs") | Out-Null
Copy-Item -LiteralPath $executable -Destination (Join-Path $packageDir "ParkerLabel.exe")
Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $archive -CompressionLevel Optimal
$verificationDir = Join-Path $env:TEMP ("ParkerLabel-verify-" + [guid]::NewGuid().ToString("N"))
try {
    Expand-Archive -LiteralPath $archive -DestinationPath $verificationDir
    if (-not (Test-Path -LiteralPath (Join-Path $verificationDir "ParkerLabel.exe") -PathType Leaf)) {
        throw "The archive does not contain ParkerLabel.exe."
    }
} finally {
    if (Test-Path -LiteralPath $verificationDir) { Remove-Item -LiteralPath $verificationDir -Recurse -Force }
}

Copy-Item -LiteralPath (Join-Path $generatedDir "build-info.json") -Destination (Join-Path $outputDir "build-info.json")
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
$checksum = "$hash  $([System.IO.Path]::GetFileName($archive))`n"
[System.IO.File]::WriteAllText((Join-Path $outputDir "SHA256SUMS"), $checksum, [System.Text.UTF8Encoding]::new($false))
$verifiedHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($verifiedHash -ne $hash) { throw "Archive checksum verification failed." }
& $python (Join-Path $projectRoot "builds\measure_bundle.py") --app $executable --archive $archive --manifest (Join-Path $projectRoot "model-bundle.json") --configs $configsDir --output (Join-Path $outputDir "size-report.json")
if ($LASTEXITCODE -ne 0) { throw "Bundle measurement failed." }

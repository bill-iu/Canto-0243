# Build Desktop release for Windows (ADR-0068: PyApp + wheel + sidecar).
# Requires: Rust/cargo, Python 3.11, client/dist-portable, lyrics.db
param(
    [switch]$SkipReadmeSync,
    [switch]$SkipPyApp,
    [string]$PyAppVersion = "latest"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "dist\canto-0243-desktop"
$ZipPath = Join-Path $Root "dist\canto-0243-desktop.zip"
$DbPath = Join-Path $Root "lyrics.db"

if (-not (Test-Path $DbPath)) {
    throw "lyrics.db not found; cannot build Desktop package."
}

$DistIndex = Join-Path $Root "client\dist-portable\index.html"
if (-not (Test-Path $DistIndex)) {
    throw "client/dist-portable/index.html not found. Run: cd client && npm run build:portable"
}

if (-not $SkipReadmeSync) {
    Write-Host "==> Sync README word count..."
    python (Join-Path $Root "scripts\update_readme_words_count.py") --db $DbPath
    if ($LASTEXITCODE -ne 0) { throw "update_readme_words_count.py failed" }
}

Write-Host "==> Clean output dir..."
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $ZipPath) -Force | Out-Null

Write-Host "==> Build wheel (canto-0243)..."
python -m pip install -q build wheel setuptools
if ($LASTEXITCODE -ne 0) { throw "pip install build tools failed" }
$WheelDir = Join-Path $Root "dist\wheels"
if (Test-Path $WheelDir) { Remove-Item $WheelDir -Recurse -Force }
New-Item -ItemType Directory -Path $WheelDir -Force | Out-Null
python -m build --wheel --outdir $WheelDir
if ($LASTEXITCODE -ne 0) { throw "python -m build failed" }
$Wheel = Get-ChildItem $WheelDir -Filter "canto_0243-*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $Wheel) { throw "wheel not produced in $WheelDir" }
Write-Host "    wheel: $($Wheel.FullName)"

Write-Host "==> Copy sidecar payload (db, UI, data, desktop launchers)..."
. (Join-Path $PSScriptRoot "desktop_bundle.ps1")
Copy-DesktopSidecar -Root $Root -OutDir $OutDir -DbPath $DbPath
Copy-Item $Wheel.FullName (Join-Path $OutDir $Wheel.Name) -Force

if ($SkipPyApp) {
    Write-Host "==> Skip PyApp (-SkipPyApp): wheel + sidecar only"
} else {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "cargo not found. Install Rust (https://rustup.rs) to build the PyApp launcher, or pass -SkipPyApp for sidecar-only."
    }
    Write-Host "==> Build PyApp launcher (CPython 3.11, embed wheel)..."
    $PyAppDir = Join-Path $Root "dist\_pyapp_src"
    if (Test-Path $PyAppDir) { Remove-Item $PyAppDir -Recurse -Force }
    New-Item -ItemType Directory -Path $PyAppDir -Force | Out-Null
    $SrcZip = Join-Path $Root "dist\pyapp-source.zip"
    if ($PyAppVersion -eq "latest") {
        $Url = "https://github.com/ofek/pyapp/releases/latest/download/source.zip"
    } else {
        $Url = "https://github.com/ofek/pyapp/releases/download/v$PyAppVersion/source.zip"
    }
    Write-Host "    download $Url"
    Invoke-WebRequest -Uri $Url -OutFile $SrcZip -UseBasicParsing
    Expand-Archive -Path $SrcZip -DestinationPath $PyAppDir -Force
    $Inner = Get-ChildItem $PyAppDir -Directory | Where-Object { $_.Name -like "pyapp*" } | Select-Object -First 1
    if (-not $Inner) { throw "pyapp source extract failed" }
    $BuildRoot = $Inner.FullName

    $env:PYAPP_PROJECT_PATH = $Wheel.FullName
    $env:PYAPP_PROJECT_NAME = "canto-0243"
    $env:PYAPP_PROJECT_VERSION = (python -c "import tomllib; print(tomllib.load(open(r'$Root\pyproject.toml','rb'))['project']['version'])")
    $env:PYAPP_PYTHON_VERSION = "3.11"
    $env:PYAPP_EXEC_SPEC = "app.desktop_entry:main"
    $env:PYAPP_IS_GUI = "1"
    # Product update path is ADR-0059 manual zip; do not market self update.
    $env:PYAPP_PIP_EXTERNAL = "1"
    $env:PYAPP_UV_ENABLED = "1"

    Push-Location $BuildRoot
    try {
        cargo build --release
        if ($LASTEXITCODE -ne 0) { throw "cargo build --release failed" }
        $Built = Join-Path $BuildRoot "target\release\pyapp.exe"
        if (-not (Test-Path $Built)) { throw "pyapp.exe not produced" }
        $ExeOut = Join-Path $OutDir "Canto-0243.exe"
        Copy-Item $Built $ExeOut -Force
        Write-Host "    launcher: $ExeOut"
    } finally {
        Pop-Location
        Remove-Item Env:PYAPP_PROJECT_PATH -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_PROJECT_NAME -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_PROJECT_VERSION -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_PYTHON_VERSION -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_EXEC_SPEC -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_IS_GUI -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_PIP_EXTERNAL -ErrorAction SilentlyContinue
        Remove-Item Env:PYAPP_UV_ENABLED -ErrorAction SilentlyContinue
    }
}

Write-Host "==> Warm word cache snapshot (.cache/word_meta.bin)..."
python (Join-Path $Root "scripts\warm_word_cache.py") $OutDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "    warn: warm_word_cache failed (non-fatal if no venv python in tree); continuing"
}

$ReleaseTag = $env:PORTABLE_RELEASE_TAG
if (-not $ReleaseTag) { $ReleaseTag = $env:DESKTOP_RELEASE_TAG }
if ($ReleaseTag) {
    Write-Host "==> Stamp portable-manifest (套件發佈指紋) tag=$ReleaseTag..."
    $Sidecar = Join-Path $Root "dist\portable-manifest-windows.json"
    python (Join-Path $Root "scripts\write_portable_manifest.py") `
        --root $OutDir --tag $ReleaseTag --platform windows --sidecar $Sidecar
    if ($LASTEXITCODE -ne 0) { throw "write_portable_manifest.py failed" }
} else {
    Write-Host "==> Skip portable-manifest (set DESKTOP_RELEASE_TAG or PORTABLE_RELEASE_TAG for release builds)"
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Write-Host "==> Create zip (Windows Desktop)..."
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal

$zipMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Done."
Write-Host "  Folder: $OutDir"
Write-Host "  ZIP:    $ZipPath (${zipMb} MB)"
Write-Host "  First run needs network (PyApp downloads CPython 3.11); then offline."
Write-Host "  macOS: scripts/build-desktop.sh on macOS"

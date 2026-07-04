# Build portable release for Windows (免安裝：內建 venv)
param(
    [switch]$SkipReadmeSync
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "dist\canto-0243-portable"
$ZipPath = Join-Path $Root "dist\canto-0243-portable.zip"

$DbPath = Join-Path $Root "lyrics.db"
if (-not (Test-Path $DbPath)) {
    throw "lyrics.db not found; cannot build portable package."
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

. (Join-Path $PSScriptRoot "portable_bundle.ps1")
Copy-PortableBundle -Root $Root -OutDir $OutDir -DbPath $DbPath

Write-Host "==> Build bundled venv (may take a few minutes)..."
python (Join-Path $Root "scripts\portable_venv.py") $OutDir
if ($LASTEXITCODE -ne 0) { throw "portable_venv.py failed" }

Write-Host "==> Smoke check bundled runtime..."
python (Join-Path $Root "scripts\portable_venv.py") $OutDir --self-check
if ($LASTEXITCODE -ne 0) { throw "portable venv self-check failed" }

Write-Host "==> Warm word cache snapshot (.cache/word_meta.bin)..."
$BundlePy = Join-Path $OutDir "venv\Scripts\python.exe"
& $BundlePy (Join-Path $Root "scripts\warm_word_cache.py") $OutDir
if ($LASTEXITCODE -ne 0) { throw "warm_word_cache.py failed" }

Write-Host "==> Build Canto-0243.exe (PyInstaller GUI launcher)..."
python -m pip install -q pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller failed" }
$PyiWork = Join-Path $Root "dist\_pyi_work"
$PyiSpec = Join-Path $Root "dist\_pyi_spec"
$Launcher = Join-Path $Root "scripts\portable_win_launcher.py"
$Icon = Join-Path $Root "frontend\favicon.ico"
if (Test-Path $PyiWork) { Remove-Item $PyiWork -Recurse -Force }
if (Test-Path $PyiSpec) { Remove-Item $PyiSpec -Recurse -Force }
$PyiArgs = @(
    "--onefile", "-w", "--clean",
    "--name", "Canto-0243",
    "--distpath", $OutDir,
    "--workpath", $PyiWork,
    "--specpath", $PyiSpec,
    $Launcher
)
if (Test-Path $Icon) { $PyiArgs = @("--icon", $Icon) + $PyiArgs }
python -m PyInstaller @PyiArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
if (-not (Test-Path (Join-Path $OutDir "Canto-0243.exe"))) {
    throw "Canto-0243.exe not produced"
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Write-Host "==> Create zip (Windows 免安裝)..."
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal

$zipMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
$dbMb = [math]::Round((Get-Item $DbPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Done."
Write-Host "  Folder: $OutDir"
Write-Host "  ZIP:    $ZipPath (${zipMb} MB) - Windows (Canto-0243.exe + START.bat)"
Write-Host "  db:     ${dbMb} MB"
Write-Host "  macOS .app: run scripts/build-portable.sh on macOS"
Write-Host "  Upload zip + macOS tar.gz + lyrics.db + words-lexicon.json to GitHub Release."

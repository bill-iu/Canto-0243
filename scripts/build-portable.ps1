# Build portable release for Windows / macOS / Linux (includes lyrics.db)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "dist\0243-lyrics-portable"
$ZipPath = Join-Path $Root "dist\0243-lyrics-portable.zip"
$TarPath = Join-Path $Root "dist\0243-lyrics-portable-macos.tar.gz"

$DbPath = Join-Path $Root "lyrics.db"
if (-not (Test-Path $DbPath)) {
    throw "lyrics.db not found; cannot build portable package."
}

Write-Host "==> Clean output dir..."
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $ZipPath) -Force | Out-Null

function Copy-Tree {
    param([string]$Src, [string]$Dst)
    if (-not (Test-Path $Src)) { return }
    robocopy $Src $Dst /E /NFL /NDL /NJH /NJS /NC /NS /NP `
        /XD __pycache__ .git venv .venv dist .agents `
        /XF *.pyc *.pyo *.log *.db.bak | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $Src" }
}

Write-Host "==> Copy app, data, frontend..."
Copy-Tree (Join-Path $Root "app") (Join-Path $OutDir "app")
Copy-Tree (Join-Path $Root "frontend") (Join-Path $OutDir "frontend")
Copy-Tree (Join-Path $Root "data") (Join-Path $OutDir "data")
Copy-Tree (Join-Path $Root "portable") $OutDir

foreach ($f in @("main.py", "utils.py", "jyutping_table.py", "requirements.txt")) {
    Copy-Item (Join-Path $Root $f) (Join-Path $OutDir $f) -Force
}

Write-Host "==> Copy lyrics.db..."
Copy-Item $DbPath (Join-Path $OutDir "lyrics.db") -Force

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Write-Host "==> Create zip (all platforms)..."
Compress-Archive -Path "$OutDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal

if (Get-Command tar -ErrorAction SilentlyContinue) {
    if (Test-Path $TarPath) { Remove-Item $TarPath -Force }
    Write-Host "==> Create macOS tar.gz (executable bits for START.sh)..."
    Push-Location (Join-Path $Root "dist")
    tar -czf $TarPath "0243-lyrics-portable"
    Pop-Location
}

$zipMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
$dbMb = [math]::Round((Get-Item $DbPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Done."
Write-Host "  Folder: $OutDir"
Write-Host "  ZIP:    $ZipPath (${zipMb} MB) - Windows / macOS / Linux"
if (Test-Path $TarPath) {
    $tarMb = [math]::Round((Get-Item $TarPath).Length / 1MB, 1)
    Write-Host "  macOS:  $TarPath (${tarMb} MB) - preferred on Mac (chmod preserved)"
}
Write-Host "  db:     ${dbMb} MB"
Write-Host "  Windows: START.bat | macOS: START.command or ./START.sh"

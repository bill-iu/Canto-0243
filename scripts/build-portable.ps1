# Deprecated name — formal channel is Desktop / PyApp (ADR-0068).
# Forwards to build-desktop.ps1. Legacy venv pack: scripts/build-portable-legacy.ps1
param(
    [switch]$SkipReadmeSync,
    [switch]$SkipPyApp,
    [switch]$NoVenvPack  # ignored; kept so old callers do not hard-fail
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Write-Host "==> build-portable.ps1 → build-desktop.ps1 (ADR-0068 Desktop/PyApp)"
$fwd = @{
    SkipReadmeSync = $SkipReadmeSync
    SkipPyApp      = $SkipPyApp
}
& (Join-Path $here "build-desktop.ps1") @fwd
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Wrapper: run gh even if PATH not refreshed after install (restart terminal to use `gh` directly).
$ghDirs = @(
    "$env:ProgramFiles\GitHub CLI",
    ${env:ProgramFiles(x86)} + "\GitHub CLI",
    "$env:LOCALAPPDATA\Programs\GitHub CLI"
)
foreach ($dir in $ghDirs) {
    $exe = Join-Path $dir "gh.exe"
    if (Test-Path $exe) {
        & $exe @args
        exit $LASTEXITCODE
    }
}
Write-Error "gh not found. Run: winget install GitHub.cli"
exit 1

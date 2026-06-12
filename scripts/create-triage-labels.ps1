# Create Matt Pocock triage labels on GitHub (idempotent).
# Prereq: gh auth login  (once per machine)
$ErrorActionPreference = "Stop"
$Repo = "ICE-U-code/0243---SQLalchemy-ORM"

function Ensure-GhInPath {
    if (Get-Command gh -ErrorAction SilentlyContinue) { return }
    $candidates = @(
        "$env:ProgramFiles\GitHub CLI",
        ${env:ProgramFiles(x86)} + "\GitHub CLI",
        "$env:LOCALAPPDATA\Programs\GitHub CLI"
    )
    foreach ($dir in $candidates) {
        if (Test-Path (Join-Path $dir "gh.exe")) {
            $env:Path = "$dir;$env:Path"
            return
        }
    }
    throw "GitHub CLI not found. Install: winget install GitHub.cli — then restart the terminal."
}
Ensure-GhInPath

$labels = @(
    @{ Name = "needs-triage";    Color = "FBCA04"; Description = "Maintainer needs to evaluate this issue" },
    @{ Name = "needs-info";      Color = "C5DEF5"; Description = "Waiting on reporter for more information" },
    @{ Name = "ready-for-agent"; Color = "7057FF"; Description = "Fully specified, ready for an AFK agent" },
    @{ Name = "ready-for-human"; Color = "1D76DB"; Description = "Requires human implementation" },
    @{ Name = "wontfix";         Color = "D93F0B"; Description = "Will not be actioned" }
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) not found. Install: winget install GitHub.cli"
}

$null = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Run: gh auth login" -ForegroundColor Yellow
    exit 1
}

$existing = @(gh label list --repo $Repo --limit 200 --json name | ConvertFrom-Json | ForEach-Object { $_.name })

foreach ($l in $labels) {
    if ($existing -contains $l.Name) {
        Write-Host "exists: $($l.Name)" -ForegroundColor DarkGray
        gh label edit $l.Name --repo $Repo --description $l.Description --color $l.Color | Out-Null
        Write-Host "updated: $($l.Name)"
    } else {
        gh label create $l.Name --repo $Repo --description $l.Description --color $l.Color
        Write-Host "created: $($l.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Done. Labels on https://github.com/$Repo/labels"

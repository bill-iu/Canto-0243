# Local Windows portable build + optional GitHub Release upload (ADR-0018).
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,
    [switch]$Upload,
    [switch]$Draft,
    [string]$NotesFile = "",
    [switch]$SkipReadmeSync
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ZipPath = Join-Path $Root "dist\canto-0243-portable.zip"
$DbPath = Join-Path $Root "lyrics.db"
$LexiconPath = Join-Path $Root "dist\words-lexicon.json"

function Invoke-Gh {
    param([string[]]$Args)
    $all = @()
    if ($env:GH_REPO) { $all += "-R", $env:GH_REPO }
    $all += $Args
    & gh @all
    if ($LASTEXITCODE -ne 0) { throw "gh failed: $($Args -join ' ')" }
}

if (-not (Test-Path $DbPath)) {
    throw "lyrics.db not found at repo root"
}

Write-Host "==> Canto-0243 local Windows release"
Write-Host "    tag:  $Tag"
Write-Host "    root: $Root"
if ($env:GH_REPO) { Write-Host "    repo: $env:GH_REPO" }

$buildArgs = @()
if ($SkipReadmeSync) { $buildArgs += "-SkipReadmeSync" }
& (Join-Path $Root "scripts\build-portable.ps1") @buildArgs
if ($LASTEXITCODE -ne 0) { throw "build-portable.ps1 failed" }

if (-not (Test-Path $ZipPath)) {
    throw "expected $ZipPath"
}

Write-Host "==> Export words-lexicon.json..."
New-Item -ItemType Directory -Path (Split-Path $LexiconPath) -Force | Out-Null
python (Join-Path $Root "scripts\export_words_lexicon.py") -o $LexiconPath
if ($LASTEXITCODE -ne 0) { throw "export_words_lexicon.py failed" }

$zipMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Built:"
Write-Host "  $ZipPath ($zipMb MB)"
Write-Host "  $LexiconPath"

if (-not $Upload) {
    Write-Host ""
    Write-Host "Done (no upload). Next: MacBook uploads x86_64 tar to the same tag."
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI required for -Upload"
}

$viewArgs = @("release", "view", $Tag)
$releaseExists = $true
try { Invoke-Gh $viewArgs | Out-Null } catch { $releaseExists = $false }

if (-not $releaseExists) {
    $title = "Canto-0243 $Tag"
    $createArgs = @("release", "create", $Tag, "--title", $title)
    if ($Draft) { $createArgs += "--draft" }
    if ($NotesFile -and (Test-Path $NotesFile)) {
        $createArgs += "--notes-file", $NotesFile
        Invoke-Gh $createArgs
    } else {
        $notes = @(
            "## Canto-0243 $Tag",
            "",
            "- Windows: ``canto-0243-portable.zip`` (this upload)",
            "- macOS Intel: ``canto-0243-portable-macos-x86_64.tar.gz`` — **待 MacBook 補上**",
            "- macOS Apple Silicon (arm64): **暫不提供**",
            "",
            "Sequoia 下載 macOS 後若被擋：系統設定 → 隱私與安全性 → 仍要開啟。"
        ) -join "`n"
        $tmp = [System.IO.Path]::GetTempFileName()
        Set-Content -Path $tmp -Value $notes -Encoding utf8NoBOM
        Invoke-Gh @($createArgs + @("--notes-file", $tmp))
        Remove-Item $tmp -Force
    }
} else {
    Write-Host "==> Release $Tag already exists; uploading assets..."
}

Write-Host "==> Upload to GitHub Release $Tag..."
Invoke-Gh @("release", "upload", $Tag, $DbPath, "--clobber")
Invoke-Gh @("release", "upload", $Tag, $LexiconPath, "--clobber")
Invoke-Gh @("release", "upload", $Tag, $ZipPath, "--clobber")

$repo = if ($env:GH_REPO) { $env:GH_REPO } else { (gh repo view --json nameWithOwner -q .nameWithOwner) }
Write-Host ""
Write-Host "Uploaded: https://github.com/$repo/releases/tag/$Tag"
Write-Host "Next: Intel MacBook — sync fork, build x86_64, upload tar (--tar-only)."

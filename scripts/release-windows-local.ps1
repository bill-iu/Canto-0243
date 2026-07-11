# Local Windows portable build + optional GitHub Release upload (ADR-0044 §5).
# Program-only tag refresh: reuse lyrics.db (local → Release download); do not re-upload lexicon assets.
# New semver with new lexicon: local build-db first; first publish uploads zip + lyrics.db + words-lexicon.json.
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,
    [switch]$Upload,
    [switch]$Draft,
    [string]$NotesFile = "",
    [switch]$SkipReadmeSync,
    # Escape hatch: upload/replace lyrics.db + words-lexicon.json even when Release already exists.
    [switch]$WithLexicon
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ZipPath = Join-Path $Root "dist\canto-0243-portable.zip"
$DbPath = Join-Path $Root "lyrics.db"
$LexiconPath = Join-Path $Root "dist\words-lexicon.json"

function Invoke-Gh {
    param([string[]]$GhArgs)
    $all = @()
    if ($env:GH_REPO) { $all += "-R", $env:GH_REPO }
    $all += $GhArgs
    & gh @all
    if ($LASTEXITCODE -ne 0) { throw "gh failed: $($GhArgs -join ' ')" }
}

function Assert-ReleaseSource {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git required to verify release source"
    }

    & git fetch origin main dev --quiet
    if ($LASTEXITCODE -ne 0) { throw "failed to fetch origin/main and origin/dev" }

    $branch = (& git branch --show-current).Trim()
    if ($branch -ne "main") {
        throw "release rebuild must run from main after dev is merged. Current branch: $branch"
    }

    $head = (& git rev-parse HEAD).Trim()
    $originMain = (& git rev-parse origin/main).Trim()
    if ($head -ne $originMain) {
        throw "local main is not at origin/main. Pull main before rebuilding release assets."
    }

    & git merge-base --is-ancestor origin/dev origin/main
    if ($LASTEXITCODE -ne 0) {
        throw "origin/dev is not merged into origin/main. Merge dev first, then rebuild release assets."
    }
}

function Test-ReleaseExists {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { return $false }
    $viewArgs = @("release", "view", $Tag)
    try {
        Invoke-Gh $viewArgs | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Ensure-LyricsDb {
    if (Test-Path $DbPath) {
        Write-Host "==> lyrics.db: using local file"
        return
    }
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw "lyrics.db missing and gh unavailable. Place lyrics.db at repo root, or install gh to download from Release $Tag."
    }
    if (-not (Test-ReleaseExists)) {
        throw @"
lyrics.db not found at repo root and Release $Tag does not exist yet.
For a new lexicon tag: python scripts/bootstrap_data.py && python -m ingest build-db
For a tag refresh: ensure the Release still has lyrics.db, or copy a previous lyrics.db to repo root.
"@
    }
    Write-Host "==> lyrics.db: downloading from Release $Tag (no build-db)..."
    Invoke-Gh @("release", "download", $Tag, "-p", "lyrics.db", "--clobber")
    if (-not (Test-Path $DbPath)) {
        throw "failed to download lyrics.db from Release $Tag (asset missing?). Do not delete lexicon assets on tag refresh."
    }
}

Write-Host "==> Canto-0243 local Windows release"
Write-Host "    tag:  $Tag"
Write-Host "    root: $Root"
if ($env:GH_REPO) { Write-Host "    repo: $env:GH_REPO" }
Assert-ReleaseSource
Ensure-LyricsDb

$buildArgs = @()
if ($SkipReadmeSync) { $buildArgs += "-SkipReadmeSync" }
& (Join-Path $Root "scripts\build-portable.ps1") @buildArgs
if ($LASTEXITCODE -ne 0) { throw "build-portable.ps1 failed" }

if (-not (Test-Path $ZipPath)) {
    throw "expected $ZipPath"
}

$releaseExists = Test-ReleaseExists
# First publish of a tag always ships lexicon (Pages + mac sync). Refresh skips unless -WithLexicon.
$uploadLexicon = $WithLexicon -or (-not $releaseExists)

if ($uploadLexicon) {
    Write-Host "==> Export words-lexicon.json..."
    New-Item -ItemType Directory -Path (Split-Path $LexiconPath) -Force | Out-Null
    $BundlePy = Join-Path $Root "dist\canto-0243-portable\venv\Scripts\python.exe"
    if (-not (Test-Path $BundlePy)) { throw "bundled python missing: $BundlePy" }
    & $BundlePy (Join-Path $Root "scripts\export_words_lexicon.py") -o $LexiconPath
    if ($LASTEXITCODE -ne 0) { throw "export_words_lexicon.py failed" }
} else {
    Write-Host "==> Skip lexicon export/upload (tag refresh; use -WithLexicon to force)"
}

$zipMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Built:"
Write-Host "  $ZipPath ($zipMb MB)"
if ($uploadLexicon) { Write-Host "  $LexiconPath" }

if (-not $Upload) {
    Write-Host ""
    Write-Host "Done (no upload). Next: MacBook uploads x86_64 tar to the same tag."
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI required for -Upload"
}

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
            "- Windows: canto-0243-portable.zip (this upload)",
            "- macOS Intel: canto-0243-portable-macos-x86_64.tar.gz (pending MacBook)",
            "- macOS Apple Silicon arm64: not available yet",
            "",
            "Sequoia Gatekeeper: System Settings, Privacy and Security, Open Anyway."
        ) -join [Environment]::NewLine
        $tmp = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($tmp, $notes)
        Invoke-Gh @($createArgs + @("--notes-file", $tmp))
        Remove-Item $tmp -Force
    }
} else {
    Write-Host "==> Release $Tag already exists; uploading zip$(if ($uploadLexicon) { ' + lexicon' } else { ' only' })..."
}

Write-Host "==> Upload to GitHub Release $Tag..."
if ($uploadLexicon) {
    Invoke-Gh @("release", "upload", $Tag, $DbPath, "--clobber")
    Invoke-Gh @("release", "upload", $Tag, $LexiconPath, "--clobber")
}
Invoke-Gh @("release", "upload", $Tag, $ZipPath, "--clobber")

$repo = if ($env:GH_REPO) { $env:GH_REPO } else { (gh repo view --json nameWithOwner -q .nameWithOwner) }
Write-Host ""
Write-Host "Uploaded: https://github.com/$repo/releases/tag/$Tag"
Write-Host 'Next: Intel MacBook sync fork, build x86_64, upload tar (--upload).'

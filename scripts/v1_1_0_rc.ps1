# One-off local release-candidate entry point for v1.1.0 only.
param(
    [ValidateSet("Plan", "Preflight", "Build", "Verify", "UploadDraft", "Finalize")]
    [string]$Mode = "Plan",
    [string]$Repository = "",
    [string]$CandidateRoot = "",
    [string]$PagesBaseUrl = "",
    [switch]$PagesVerified
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Repository) { $Repository = $Root }
$Repository = [System.IO.Path]::GetFullPath($Repository)
if (-not $CandidateRoot) { $CandidateRoot = $Root }
$CandidateRoot = [System.IO.Path]::GetFullPath($CandidateRoot)
$Tag = "v1.1.0"
$Artifacts = @(
    "lyrics.db",
    "dist/words-lexicon.json",
    "dist/canto-0243-portable.zip",
    "dist/portable-manifest-windows.json",
    "dist/canto-0243-pages-v1.1.0.tar.gz",
    "dist/v1.1.0-SHA256SUMS.txt"
)
$BuildCommands = @(
    "python scripts/fetch/fetch_rime_data.py",
    "python -m ingest build-db",
    "python tests/smoke/test_v1_1_0_rc.py",
    "npm ci (client)",
    "POS self-checks",
    "npm run build:portable + portable-host self-check (client)",
    "npm run build (client)",
    "python scripts/v1_1_0_rc.py pack-pages",
    "scripts/release-windows-local.ps1 -Tag v1.1.0",
    "python scripts/v1_1_0_rc.py write-checksums",
    "python scripts/v1_1_0_rc.py create-manifest"
)
$PublishCommands = @(
    "python scripts/v1_1_0_rc.py verify-manifest",
    "gh release create v1.1.0 --draft",
    "gh release upload v1.1.0 (accepted artifacts)",
    "gh workflow run pages-v1.1.0.yml",
    "gh release edit v1.1.0 --draft=false"
)

if ($Mode -eq "Plan") {
    [ordered]@{
        tag = $Tag
        artifacts = $Artifacts
        build_commands = $BuildCommands
        publish_commands = $PublishCommands
        finalize_checks = @(
            "pages-v1.1.0 workflow completed successfully"
            "live Pages DB/search/POS smoke"
        )
    } | ConvertTo-Json -Depth 4
    exit 0
}

function Invoke-GitText {
    param([string[]]$GitArgs)
    $value = & git -C $Repository @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git failed: $($GitArgs -join ' ')" }
    return ($value | Out-String).Trim()
}

function Assert-ReleaseSource {
    $branch = Invoke-GitText @("branch", "--show-current")
    if ($branch -ne "main") {
        throw "v1.1.0 RC must run from main; current branch: $branch"
    }
    $dirty = Invoke-GitText @("status", "--porcelain")
    if ($dirty) { throw "v1.1.0 RC requires a clean main worktree" }
    $head = Invoke-GitText @("rev-parse", "HEAD")
    $originMain = Invoke-GitText @("rev-parse", "origin/main")
    if ($head -ne $originMain) { throw "local main must exactly match origin/main" }
    & git -C $Repository merge-base --is-ancestor origin/dev origin/main
    if ($LASTEXITCODE -ne 0) { throw "origin/dev must be merged into origin/main" }
    & git -C $Repository show-ref --verify --quiet "refs/tags/$Tag"
    if ($LASTEXITCODE -eq 0) {
        $tagCommit = Invoke-GitText @("rev-parse", "refs/tags/$Tag^{commit}")
        if ($tagCommit -ne $head) { throw "$Tag already points to another commit" }
    }
    return $head
}

function Invoke-Checked {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $Root
    )
    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "command failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-GhChecked {
    param([string[]]$GhArgs)
    $arguments = @()
    if ($env:GH_REPO) { $arguments += @("-R", $env:GH_REPO) }
    $arguments += $GhArgs
    & gh @arguments
    if ($LASTEXITCODE -ne 0) { throw "gh failed: $($GhArgs -join ' ')" }
}

function Invoke-GhJson {
    param([string[]]$GhArgs)
    $arguments = @()
    if ($env:GH_REPO) { $arguments += @("-R", $env:GH_REPO) }
    $arguments += $GhArgs
    $json = & gh @arguments
    if ($LASTEXITCODE -ne 0) { throw "gh failed: $($GhArgs -join ' ')" }
    return (($json | Out-String) | ConvertFrom-Json)
}

function Get-ReleaseOrNull {
    $arguments = @()
    if ($env:GH_REPO) { $arguments += @("-R", $env:GH_REPO) }
    $arguments += @("release", "view", $Tag, "--json", "tagName,isDraft,isPrerelease,assets")
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $json = & gh @arguments 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
    } finally {
        $ErrorActionPreference = $previous
    }
    return ($json | Out-String | ConvertFrom-Json)
}

function Assert-Candidate {
    param([string]$Commit)
    $manifest = Join-Path $CandidateRoot "dist\v1.1.0-rc-manifest.json"
    $output = & python (Join-Path $Root "scripts\v1_1_0_rc.py") verify-manifest `
        --tag $Tag --root $CandidateRoot --source-commit $Commit --manifest $manifest
    if ($LASTEXITCODE -ne 0) { throw "v1.1.0 RC manifest verification failed: $output" }
}

function Assert-RemoteCandidate {
    param([string]$Commit)
    $manifest = Join-Path $CandidateRoot "dist\v1.1.0-rc-manifest.json"
    $remoteDir = Join-Path ([IO.Path]::GetTempPath()) ("canto-v1.1.0-finalize-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $remoteDir | Out-Null
    try {
        Invoke-GhChecked @("release", "download", $Tag, "-D", $remoteDir)
        $result = & python (Join-Path $Root "scripts\v1_1_0_rc.py") verify-remote-assets `
            --root $CandidateRoot --remote-dir $remoteDir --manifest $manifest --source-commit $Commit
        if ($LASTEXITCODE -ne 0) { throw "remote draft assets differ from accepted candidate: $result" }
        if (@((($result | Out-String) | ConvertFrom-Json).missing).Count -ne 0) {
            throw "remote draft is missing accepted candidate assets"
        }
    } finally {
        if (Test-Path -LiteralPath $remoteDir) { Remove-Item -LiteralPath $remoteDir -Recurse -Force }
    }
}

function Test-RelocatedPortable {
    $zip = Join-Path $Root "dist\canto-0243-portable.zip"
    $extract = Join-Path ([IO.Path]::GetTempPath()) ("canto-v1.1.0-portable-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $extract | Out-Null
    $process = $null
    try {
        Expand-Archive -LiteralPath $zip -DestinationPath $extract
        $python = Join-Path $extract "venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $python)) { throw "relocated portable is missing bundled Python" }
        $listener = [System.Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
        $listener.Start()
        $port = ([Net.IPEndPoint]$listener.LocalEndpoint).Port
        $listener.Stop()
        $oldValues = @{}
        foreach ($name in @("PORT", "HOST", "PORTABLE", "ENV", "PYTHONUTF8", "PYTHONIOENCODING")) {
            $oldValues[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
        }
        try {
            $env:PORT = "$port"; $env:HOST = "127.0.0.1"; $env:PORTABLE = "1"; $env:ENV = "local"
            $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
            $stdout = Join-Path $extract "rc-smoke.out.log"
            $stderr = Join-Path $extract "rc-smoke.err.log"
            $process = Start-Process -FilePath $python -ArgumentList "main.py" -WorkingDirectory $extract `
                -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
        } finally {
            foreach ($name in $oldValues.Keys) {
                [Environment]::SetEnvironmentVariable($name, $oldValues[$name], "Process")
            }
        }
        $ready = $null
        for ($attempt = 0; $attempt -lt 180; $attempt++) {
            try {
                $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$port/ready" -TimeoutSec 1
                if ($ready.gate_ready) { break }
            } catch {}
            Start-Sleep -Milliseconds 500
        }
        if ($null -eq $ready -or -not $ready.gate_ready -or -not $ready.portable) {
            throw "relocated portable readiness smoke failed"
        }
        $search = @(Invoke-RestMethod -Uri "http://127.0.0.1:$port/words/search/?q=23" -TimeoutSec 15)
        if ($search.Count -eq 0) { throw "relocated portable search smoke returned no results" }
        $shutdown = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$port/shutdown" -TimeoutSec 5
        if (-not $shutdown.ok) { throw "relocated portable shutdown smoke failed" }
        if (-not $process.WaitForExit(10000)) { throw "relocated portable did not exit after shutdown" }
    } finally {
        if ($null -ne $process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
        if (Test-Path -LiteralPath $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
    }
}

if ($Mode -eq "Preflight") {
    $commit = Assert-ReleaseSource
    [ordered]@{ tag = $Tag; source_commit = $commit; repository = $Repository } |
        ConvertTo-Json -Depth 3
    exit 0
}

if ($Mode -eq "Verify") {
    $commit = Assert-ReleaseSource
    Assert-Candidate $commit
    [ordered]@{ tag = $Tag; source_commit = $commit; verified = $true } |
        ConvertTo-Json -Depth 3
    exit 0
}

if ($Mode -eq "Build") {
    $branch = Invoke-GitText @("branch", "--show-current")
    if ($branch -ne "main") { throw "v1.1.0 RC must run from main; current branch: $branch" }
    if ($Repository -ne $Root -or $CandidateRoot -ne $Root) {
        throw "Build only supports the Canto-0243 repository root"
    }
    Invoke-Checked "git" @("fetch", "origin", "main", "dev", "--tags", "--quiet") $Root
    $commit = Assert-ReleaseSource

    Invoke-Checked "python" @("scripts/fetch/fetch_rime_data.py") $Root
    Invoke-Checked "python" @("-m", "ingest", "build-db") $Root
    Invoke-Checked "python" @("-m", "ingest.project_pos", "check") $Root
    Invoke-Checked "python" @("tests/smoke/test_v1_1_0_rc.py") $Root

    $previousReleaseTag = $env:RELEASE_TAG
    $previousLexiconVersion = $env:VITE_LEXICON_VERSION
    try {
        $env:RELEASE_TAG = $Tag
        $env:VITE_LEXICON_VERSION = $Tag
        Invoke-Checked "npm.cmd" @("ci") (Join-Path $Root "client")
        Invoke-Checked "npx.cmd" @("--no-install", "tsx", "scripts/pos-meta-self-check.ts") (Join-Path $Root "client")
        Invoke-Checked "npx.cmd" @("--no-install", "tsx", "scripts/pos-filter-self-check.ts") (Join-Path $Root "client")
        Invoke-Checked "npm.cmd" @("run", "build:portable") (Join-Path $Root "client")
        Invoke-Checked "node" @("scripts/portable-host-build-self-check.mjs") (Join-Path $Root "client")
        Invoke-Checked "npm.cmd" @("run", "build") (Join-Path $Root "client")
    } finally {
        $env:RELEASE_TAG = $previousReleaseTag
        $env:VITE_LEXICON_VERSION = $previousLexiconVersion
    }

    Invoke-Checked "python" @(
        "scripts/v1_1_0_rc.py", "pack-pages",
        "--tag", $Tag,
        "--root", $Root,
        "--source-dir", (Join-Path $Root "client/dist"),
        "--output", (Join-Path $Root "dist/canto-0243-pages-v1.1.0.tar.gz")
    ) $Root

    & (Join-Path $Root "scripts/release-windows-local.ps1") `
        -Tag $Tag -SkipReadmeSync -WithLexicon
    Test-RelocatedPortable

    Invoke-Checked "python" @(
        "scripts/v1_1_0_rc.py", "write-checksums",
        "--root", $Root,
        "--output", (Join-Path $Root "dist/v1.1.0-SHA256SUMS.txt")
    ) $Root

    Invoke-Checked "python" @(
        "scripts/v1_1_0_rc.py", "create-manifest",
        "--tag", $Tag,
        "--root", $Root,
        "--source-commit", $commit,
        "--passed-check", "build-db",
        "--passed-check", "project-pos",
        "--passed-check", "rc-contract",
        "--passed-check", "pos-self-checks",
        "--passed-check", "portable-host-build",
        "--passed-check", "pwa-build",
        "--passed-check", "pages-package",
        "--passed-check", "windows-portable",
        "--passed-check", "relocated-portable-smoke",
        "--output", (Join-Path $Root "dist/v1.1.0-rc-manifest.json")
    ) $Root
    Write-Host "v1.1.0 RC built. Run -Mode Verify, then complete local acceptance."
    exit 0
}

if ($Mode -eq "UploadDraft") {
    $branch = Invoke-GitText @("branch", "--show-current")
    if ($branch -ne "main") { throw "v1.1.0 RC must run from main; current branch: $branch" }
    if ($Repository -ne $Root -or $CandidateRoot -ne $Root) {
        throw "UploadDraft only supports the Canto-0243 repository root"
    }
    Invoke-Checked "git" @("fetch", "origin", "main", "dev", "--tags", "--quiet") $Root
    $commit = Assert-ReleaseSource
    Assert-Candidate $commit

    $release = Get-ReleaseOrNull
    if ($null -eq $release) {
        Invoke-GhChecked @(
            "release", "create", $Tag,
            "--target", $commit,
            "--title", "Canto-0243 v1.1.0",
            "--draft",
            "--notes", "Windows x64 and Pages release candidate accepted locally. macOS Intel tar pending."
        )
    } elseif (-not $release.isDraft) {
        throw "$Tag already has a non-draft release"
    }

    $manifestPath = Join-Path $Root "dist\v1.1.0-rc-manifest.json"
    $uploadPaths = @($Artifacts | ForEach-Object { Join-Path $Root $_ }) + @($manifestPath)
    $uploadByName = @{}
    foreach ($path in $uploadPaths) { $uploadByName[[IO.Path]::GetFileName($path)] = $path }
    $remoteDir = Join-Path ([IO.Path]::GetTempPath()) ("canto-v1.1.0-release-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $remoteDir | Out-Null
    try {
        if (@($release.assets).Count -gt 0) {
            Invoke-GhChecked @("release", "download", $Tag, "-D", $remoteDir)
        }
        $retryJson = & python (Join-Path $Root "scripts\v1_1_0_rc.py") verify-remote-assets `
            --root $Root --remote-dir $remoteDir --manifest $manifestPath --source-commit $commit
        if ($LASTEXITCODE -ne 0) { throw "remote draft assets differ from accepted candidate" }
        $missingNames = @((($retryJson | Out-String) | ConvertFrom-Json).missing)
        if ($missingNames.Count -gt 0) {
            $missingPaths = @($missingNames | ForEach-Object { $uploadByName[$_] })
            if ($missingPaths -contains $null) { throw "unknown missing asset returned by verifier" }
            Invoke-GhChecked (@("release", "upload", $Tag) + $missingPaths)
        }
    } finally {
        if (Test-Path -LiteralPath $remoteDir) { Remove-Item -LiteralPath $remoteDir -Recurse -Force }
    }

    $remote = Get-ReleaseOrNull
    if ($null -eq $remote -or -not $remote.isDraft) { throw "expected a v1.1.0 draft release" }
    $expectedSizes = @{}
    foreach ($path in $uploadPaths) { $expectedSizes[[IO.Path]::GetFileName($path)] = (Get-Item $path).Length }
    foreach ($name in $expectedSizes.Keys) {
        $asset = @($remote.assets | Where-Object { $_.name -eq $name })
        if ($asset.Count -ne 1 -or [int64]$asset[0].size -ne [int64]$expectedSizes[$name]) {
            throw "remote release asset mismatch: $name"
        }
    }
    if (@($remote.assets).Count -ne $expectedSizes.Count) {
        throw "remote release contains unexpected assets"
    }

    Invoke-GhChecked @("workflow", "run", "pages-v1.1.0.yml", "--ref", "main")
    Write-Host "v1.1.0 draft uploaded and Pages deployment dispatched. Do not finalize before live verification."
    exit 0
}

if ($Mode -eq "Finalize") {
    if (-not $PagesVerified) {
        throw "Finalize requires -PagesVerified after live v1.1.0 Pages acceptance"
    }
    $branch = Invoke-GitText @("branch", "--show-current")
    if ($branch -ne "main") { throw "v1.1.0 RC must run from main; current branch: $branch" }
    if ($Repository -ne $Root -or $CandidateRoot -ne $Root) {
        throw "Finalize only supports the Canto-0243 repository root"
    }
    Invoke-Checked "git" @("fetch", "origin", "main", "dev", "--tags", "--quiet") $Root
    $commit = Assert-ReleaseSource
    Assert-Candidate $commit
    $release = Get-ReleaseOrNull
    if ($null -eq $release -or -not $release.isDraft) { throw "expected a v1.1.0 draft release" }
    Assert-RemoteCandidate $commit

    $runs = @(Invoke-GhJson @(
        "run", "list",
        "--workflow", "pages-v1.1.0.yml",
        "--branch", "main",
        "--event", "workflow_dispatch",
        "--commit", $commit,
        "--limit", "10",
        "--json", "databaseId,status,conclusion,headSha,url"
    ))
    $successfulRun = @($runs | Where-Object {
        $_.headSha -eq $commit -and $_.status -eq "completed" -and $_.conclusion -eq "success"
    } | Select-Object -First 1)
    if ($successfulRun.Count -ne 1) {
        throw "pages-v1.1.0 workflow has not completed successfully for $commit"
    }

    if (-not $PagesBaseUrl) {
        $repoInfo = Invoke-GhJson @("repo", "view", "--json", "nameWithOwner")
        $pagesInfo = Invoke-GhJson @("api", "repos/$($repoInfo.nameWithOwner)/pages")
        $PagesBaseUrl = [string]$pagesInfo.html_url
    }
    if (-not $PagesBaseUrl) { throw "could not resolve the GitHub Pages URL" }
    Invoke-Checked "python" @(
        "scripts/v1_1_0_rc.py", "live-smoke",
        "--root", $CandidateRoot,
        "--base-url", $PagesBaseUrl
    ) $Root
    Invoke-GhChecked @("release", "edit", $Tag, "--draft=false", "--prerelease=false", "--latest")
    Write-Host "v1.1.0 published as the formal release. macOS Intel assets may be added later."
    exit 0
}

throw "$Mode is not implemented yet"

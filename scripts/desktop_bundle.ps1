# Shared Desktop sidecar copy (Windows) — ADR-0068 (no app/ Python tree; wheel carries code).

function Copy-DesktopSidecar {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$OutDir,
        [Parameter(Mandatory = $true)][string]$DbPath
    )

    function Copy-Tree {
        param(
            [string]$Src,
            [string]$Dst,
            [string[]]$ExcludeDirs = @("__pycache__", ".git", "venv", ".venv", "dist", ".agents", "macos")
        )
        if (-not (Test-Path $Src)) { return }
        New-Item -ItemType Directory -Path $Dst -Force | Out-Null
        $xd = @("/XD") + $ExcludeDirs
        robocopy $Src $Dst /E /NFL /NDL /NJH /NJS /NC /NS /NP `
            @xd `
            /XF *.pyc *.pyo *.log *.db.bak | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $Src -> $Dst" }
    }

    $DistPortable = Join-Path $Root "client\dist-portable"
    $DistIndex = Join-Path $DistPortable "index.html"
    if (-not (Test-Path $DistIndex)) {
        throw "client/dist-portable/index.html not found. Run: cd client && npm run build:portable"
    }

    Write-Host "    UI + data + launcher templates..."
    $UiOut = Join-Path $OutDir "client\dist-portable"
    Copy-Tree $DistPortable $UiOut
    # ADR-0068 §13: drop PWA browser-engine dead weight (query = root lyrics.db + API).
    python (Join-Path $Root "scripts\desktop_ui_strip.py") $UiOut
    if ($LASTEXITCODE -ne 0) { throw "desktop_ui_strip.py failed" }

    $DataExclude = @(
        "__pycache__", ".git", "venv", ".venv", "dist", ".agents", "macos",
        "audit", "fixtures", "raw", "proposals", "locks", "pos", "project"
    )
    Copy-Tree (Join-Path $Root "data") (Join-Path $OutDir "data") -ExcludeDirs $DataExclude

    # Desktop ships .exe only (no START.bat). README + env seed still ok.
    foreach ($name in @("README.txt", "env.portable")) {
        $src = Join-Path $Root "portable\$name"
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $OutDir $name) -Force
        }
    }

    python (Join-Path $Root "scripts\portable_data_slim.py") (Join-Path $OutDir "data")
    if ($LASTEXITCODE -ne 0) { throw "portable_data_slim.py failed" }

    Copy-Item $DbPath (Join-Path $OutDir "lyrics.db") -Force
}

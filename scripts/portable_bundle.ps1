# Shared portable bundle file copy (Windows)

function Copy-PortableBundle {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$OutDir,
        [Parameter(Mandatory = $true)][string]$DbPath
    )

    function Copy-PortableTree {
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

    Write-Host "==> Copy app, data, client/dist-portable, portable launchers..."
    Copy-PortableTree (Join-Path $Root "app") (Join-Path $OutDir "app")
    Copy-PortableTree $DistPortable (Join-Path $OutDir "client\dist-portable")
    # C11-B: skip audit/fixtures/raw/pos/project at copy; slim removes campaign leftovers.
    $DataExclude = @(
        "__pycache__", ".git", "venv", ".venv", "dist", ".agents", "macos",
        "audit", "fixtures", "raw", "proposals", "locks", "pos", "project"
    )
    Copy-PortableTree (Join-Path $Root "data") (Join-Path $OutDir "data") -ExcludeDirs $DataExclude
    Copy-PortableTree (Join-Path $Root "portable") $OutDir

    foreach ($f in @("main.py", "requirements.txt")) {
        Copy-Item (Join-Path $Root $f) (Join-Path $OutDir $f) -Force
    }

    Write-Host "==> Slim portable data (C11-B)..."
    python (Join-Path $Root "scripts\portable_data_slim.py") (Join-Path $OutDir "data")
    if ($LASTEXITCODE -ne 0) { throw "portable_data_slim.py failed" }

    Write-Host "==> Copy lyrics.db..."
    Copy-Item $DbPath (Join-Path $OutDir "lyrics.db") -Force
}

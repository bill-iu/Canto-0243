# Shared portable bundle file copy (Windows)

function Copy-PortableBundle {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$OutDir,
        [Parameter(Mandatory = $true)][string]$DbPath
    )

    function Copy-PortableTree {
        param([string]$Src, [string]$Dst)
        if (-not (Test-Path $Src)) { return }
        New-Item -ItemType Directory -Path $Dst -Force | Out-Null
        robocopy $Src $Dst /E /NFL /NDL /NJH /NJS /NC /NS /NP `
            /XD __pycache__ .git venv .venv dist .agents macos `
            /XF *.pyc *.pyo *.log *.db.bak | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $Src -> $Dst" }
    }

    Write-Host "==> Copy app, data, frontend, portable launchers..."
    Copy-PortableTree (Join-Path $Root "app") (Join-Path $OutDir "app")
    Copy-PortableTree (Join-Path $Root "frontend") (Join-Path $OutDir "frontend")
    Copy-PortableTree (Join-Path $Root "data") (Join-Path $OutDir "data")
    Copy-PortableTree (Join-Path $Root "portable") $OutDir

    foreach ($f in @("main.py", "requirements.txt")) {
        Copy-Item (Join-Path $Root $f) (Join-Path $OutDir $f) -Force
    }

    Write-Host "==> Copy lyrics.db..."
    Copy-Item $DbPath (Join-Path $OutDir "lyrics.db") -Force
}

# ADR-0067: extract venv.pack -> venv/ without system Python (START.bat path).
# Contract mirrors scripts/portable_venv_pack.py (marker / lock / delete pack).
param(
    [Parameter(Mandatory = $true)][string]$Root
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath $Root).Path
$PackName = "venv.pack"
$MarkerName = ".portable-venv-extracted"
$LockName = ".portable-venv-extract.lock"
$Pack = Join-Path $Root $PackName
$Venv = Join-Path $Root "venv"
$Marker = Join-Path $Venv $MarkerName
$Lock = Join-Path $Venv $LockName

function Get-Sha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-VenvOk {
    $py = Join-Path $Venv "Scripts\python.exe"
    $homePy = Join-Path $Venv "python-home\python.exe"
    return (Test-Path -LiteralPath $py) -and (Test-Path -LiteralPath $homePy)
}

function Clear-VenvTree {
    if (-not (Test-Path -LiteralPath $Venv)) { return }
    Get-ChildItem -LiteralPath $Venv -Force | ForEach-Object {
        if ($_.Name -eq $LockName) { return }
        Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path -LiteralPath $Pack)) {
    if (Test-VenvOk) { exit 0 }
    Write-Host "[ERROR] No venv.pack and no usable venv. Re-download the full portable package."
    exit 1
}

if (-not (Test-Path -LiteralPath $Venv)) {
    New-Item -ItemType Directory -Path $Venv -Force | Out-Null
}

$deadline = (Get-Date).AddMinutes(10)
while ($true) {
    try {
        $fs = [System.IO.File]::Open($Lock, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $bytes = [System.Text.Encoding]::ASCII.GetBytes("$PID")
        $fs.Write($bytes, 0, $bytes.Length)
        $fs.Close()
        break
    } catch {
        if ((Get-Date) -ge $deadline) {
            Write-Host "[ERROR] venv extract lock busy: $Lock"
            exit 1
        }
        Start-Sleep -Milliseconds 500
        if (Test-Path -LiteralPath $Lock) {
            $age = (Get-Date) - (Get-Item -LiteralPath $Lock).LastWriteTime
            if ($age.TotalMinutes -gt 10) {
                Remove-Item -LiteralPath $Lock -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

$failed = $false
try {
    if (-not (Test-Path -LiteralPath $Pack)) {
        if (Test-VenvOk) { exit 0 }
        throw "venv.pack disappeared"
    }
    $sha = Get-Sha256 $Pack
    if ((Test-Path -LiteralPath $Marker) -and (Test-VenvOk)) {
        try {
            $m = Get-Content -LiteralPath $Marker -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($m.pack_sha256 -eq $sha) {
                Remove-Item -LiteralPath $Pack -Force -ErrorAction SilentlyContinue
                exit 0
            }
        } catch { }
    }

    Write-Host "First-run: extracting runtime from venv.pack ..."
    Clear-VenvTree

    # Stage into temp dir (Expand-Archive wants a clean destination)
    $stage = Join-Path $Root ("venv._extract_" + $PID)
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
    New-Item -ItemType Directory -Path $stage -Force | Out-Null

    # ZipFile (venv.pack is zip; Expand-Archive rejects non-.zip names)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($Pack)
    try {
        $fileEntries = @($archive.Entries | Where-Object { -not $_.FullName.EndsWith("/") -and $_.Name })
        $total = $fileEntries.Count
        $n = 0
        foreach ($entry in $fileEntries) {
            $n++
            $parts = $entry.FullName.Split(@('/'), [System.StringSplitOptions]::RemoveEmptyEntries)
            $dest = $stage
            foreach ($part in $parts) {
                $dest = Join-Path $dest $part
            }
            $parent = Split-Path -Parent $dest
            if ($parent -and -not (Test-Path -LiteralPath $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            $inStream = $entry.Open()
            try {
                $outStream = [System.IO.File]::Create($dest)
                try {
                    $inStream.CopyTo($outStream)
                } finally {
                    $outStream.Close()
                }
            } finally {
                $inStream.Close()
            }
            if ($total -gt 0 -and ($n -eq 1 -or $n -eq $total -or ($n % [Math]::Max(1, [int]($total / 20))) -eq 0)) {
                $pct = [int](100 * $n / $total)
                Write-Host ("  extract " + $n + "/" + $total + " (" + $pct + " pct)")
            }
        }
    } finally {
        $archive.Dispose()
    }

    # Move staged tree into venv/
    Get-ChildItem -LiteralPath $stage -Force | ForEach-Object {
        $dest = Join-Path $Venv $_.Name
        Move-Item -LiteralPath $_.FullName -Destination $dest -Force
    }
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue

    if (-not (Test-VenvOk)) {
        throw "extract finished but venv python missing"
    }

    $unix = [int]((Get-Date).ToUniversalTime() - [datetime]"1970-01-01").TotalSeconds
    $markerJson = '{"pack_sha256":"' + $sha + '","extracted_at":' + $unix + '}' + "`n"
    [System.IO.File]::WriteAllText($Marker, $markerJson)
    Remove-Item -LiteralPath $Pack -Force
    Write-Host "Runtime extract done."
} catch {
    $failed = $true
    Write-Host ("[ERROR] venv extract failed: " + $_.Exception.Message)
    Clear-VenvTree
} finally {
    if (Test-Path -LiteralPath $Lock) {
        Remove-Item -LiteralPath $Lock -Force -ErrorAction SilentlyContinue
    }
}

if ($failed) { exit 1 }
exit 0

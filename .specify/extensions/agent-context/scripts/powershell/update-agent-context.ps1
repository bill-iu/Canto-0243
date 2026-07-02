#!/usr/bin/env pwsh
# update-agent-context.ps1
#
# Refresh the managed Spec Kit section in the coding agent's context file
# (e.g. CLAUDE.md, .github/copilot-instructions.md, AGENTS.md).
#
# Reads `context_file` and `context_markers.{start,end}` from the
# agent-context extension config:
#   .specify/extensions/agent-context/agent-context-config.yml
#
# Usage: update-agent-context.ps1 [plan_path]

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$PlanPath
)

function Get-ConfigValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string]$Key
    )

    if ($null -eq $Object) {
        return $null
    }
    if ($Object -is [System.Collections.IDictionary]) {
        return $Object[$Key]
    }
    $prop = $Object.PSObject.Properties[$Key]
    if ($prop) {
        return $prop.Value
    }
    return $null
}

function Test-ConfigObject {
    param(
        [AllowNull()][object]$Object
    )

    if ($null -eq $Object) {
        return $false
    }
    if ($Object -is [System.Collections.IDictionary]) {
        return $true
    }
    if ($Object -is [System.Management.Automation.PSCustomObject]) {
        return $true
    }
    return $false
}

$ErrorActionPreference = 'Stop'
$DefaultStart = '<!-- SPECKIT START -->'
$DefaultEnd   = '<!-- SPECKIT END -->'
$ProjectRoot  = (Get-Location).Path
$ExtConfig    = Join-Path $ProjectRoot '.specify/extensions/agent-context/agent-context-config.yml'

if (-not (Test-Path -LiteralPath $ExtConfig)) {
    Write-Warning "agent-context: $ExtConfig not found; nothing to do."
    exit 0
}

if ($null -ne $PlanPath) {
    $PlanPath = $PlanPath.Trim()
}

$Options = $null
if (Get-Command ConvertFrom-Yaml -ErrorAction SilentlyContinue) {
    try {
        $Options = Get-Content -LiteralPath $ExtConfig -Raw | ConvertFrom-Yaml -ErrorAction Stop
    } catch {
        # fall through to Python fallback
    }
}

if ($null -eq $Options) {
    # ConvertFrom-Yaml unavailable or failed; parse minimal YAML subset.
    # ponytail: We only need a few scalar keys; avoid extra deps.
    try {
        $raw = Get-Content -LiteralPath $ExtConfig -Raw
        $opts = @{}

        $m = [regex]::Match($raw, '(?m)^\s*context_file\s*:\s*(.+?)\s*$')
        if ($m.Success) { $opts['context_file'] = $m.Groups[1].Value.Trim() }

        $start = [regex]::Match($raw, '(?m)^\s*start\s*:\s*(.+?)\s*$')
        $end   = [regex]::Match($raw, '(?m)^\s*end\s*:\s*(.+?)\s*$')
        $cm = @{}
        if ($start.Success) { $cm['start'] = $start.Groups[1].Value.Trim() }
        if ($end.Success)   { $cm['end']   = $end.Groups[1].Value.Trim() }
        if ($cm.Count -gt 0) { $opts['context_markers'] = $cm }

        $Options = $opts
    } catch {
        $Options = $null
    }

    if (-not $Options -or $Options.Count -eq 0) {
        Write-Warning "agent-context: unable to parse $ExtConfig; skipping update."
        exit 0
    }
}

if (-not (Test-ConfigObject -Object $Options)) {
    Write-Warning "agent-context: $ExtConfig must contain a YAML mapping; skipping update."
    exit 0
}

$ContextFile = Get-ConfigValue -Object $Options -Key 'context_file'
if (-not $ContextFile) {
    Write-Warning 'agent-context: context_file not set in extension config; nothing to do.'
    exit 0
}

# Reject absolute paths and '..' path segments in context_file
if ([System.IO.Path]::IsPathRooted($ContextFile)) {
    Write-Warning "agent-context: context_file must be a project-relative path; got '$ContextFile'."
    exit 1
}
$cfSegments = $ContextFile -split '[/\\]'
if ($cfSegments -contains '..') {
    Write-Warning "agent-context: context_file must not contain '..' path segments; got '$ContextFile'."
    exit 1
}

$MarkerStart = $DefaultStart
$MarkerEnd   = $DefaultEnd
$cm = Get-ConfigValue -Object $Options -Key 'context_markers'
if ($cm) {
    $cmStart = Get-ConfigValue -Object $cm -Key 'start'
    if ($cmStart -is [string] -and $cmStart) {
        $MarkerStart = $cmStart
    }
    $cmEnd = Get-ConfigValue -Object $cm -Key 'end'
    if ($cmEnd -is [string] -and $cmEnd) {
        $MarkerEnd = $cmEnd
    }
}

if (-not $PlanPath) {
    # Prefer feature.json if present (single source of truth for current feature dir)
    try {
        $featureJson = Join-Path $ProjectRoot '.specify/feature.json'
        if (Test-Path -LiteralPath $featureJson) {
            $fj = Get-Content -LiteralPath $featureJson -Raw | ConvertFrom-Json -ErrorAction Stop
            $fd = Get-ConfigValue -Object $fj -Key 'feature_directory'
            if ($fd) {
                $planCandidate = Join-Path (Join-Path $ProjectRoot $fd) 'plan.md'
                if (Test-Path -LiteralPath $planCandidate) {
                    $PlanPath = [System.IO.Path]::GetRelativePath($ProjectRoot, $planCandidate).Replace('\','/')
                }
            }
        }
    } catch {
        # Non-fatal: fall back to directory scan.
    }

    # Discover plan.md exactly one level deep (specs/<feature>/plan.md),
    # matching the bash glob specs/*/plan.md. Wrap in try/catch so access errors under
    # $ErrorActionPreference = 'Stop' don't abort the script.
    try {
        $specsDir = Join-Path $ProjectRoot 'specs'
        $candidate = Get-ChildItem -Path $specsDir -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Get-Item -LiteralPath (Join-Path $_.FullName 'plan.md') -ErrorAction SilentlyContinue } |
            Where-Object { $_ } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($candidate) {
            $PlanPath = [System.IO.Path]::GetRelativePath($ProjectRoot, $candidate.FullName).Replace('\','/')
        }
    } catch {
        # Non-fatal: continue without a plan path.
    }
}

$CtxPath = Join-Path $ProjectRoot $ContextFile
$CtxDir  = Split-Path -Parent $CtxPath
if ($CtxDir -and -not (Test-Path -LiteralPath $CtxDir)) {
    New-Item -ItemType Directory -Path $CtxDir -Force | Out-Null
}

$lines = @($MarkerStart,
           'For additional context about technologies to be used, project structure,',
           'shell commands, and other important information, read the current plan')
if ($PlanPath) {
    $lines += "at $PlanPath"
}
$lines += $MarkerEnd
$Section = ($lines -join "`n") + "`n"

if (Test-Path -LiteralPath $CtxPath) {
    $rawBytes = [System.IO.File]::ReadAllBytes($CtxPath)
    # Strip UTF-8 BOM if present
    if ($rawBytes.Length -ge 3 -and $rawBytes[0] -eq 0xEF -and $rawBytes[1] -eq 0xBB -and $rawBytes[2] -eq 0xBF) {
        $content = [System.Text.Encoding]::UTF8.GetString($rawBytes, 3, $rawBytes.Length - 3)
    } else {
        $content = [System.Text.Encoding]::UTF8.GetString($rawBytes)
    }

    $s = $content.IndexOf($MarkerStart)
    $e = if ($s -ge 0) { $content.IndexOf($MarkerEnd, $s) } else { $content.IndexOf($MarkerEnd) }

    if ($s -ge 0 -and $e -ge 0 -and $e -gt $s) {
        $endOfMarker = $e + $MarkerEnd.Length
        if ($endOfMarker -lt $content.Length -and $content[$endOfMarker] -eq "`r") { $endOfMarker++ }
        if ($endOfMarker -lt $content.Length -and $content[$endOfMarker] -eq "`n") { $endOfMarker++ }
        $newContent = $content.Substring(0, $s) + $Section + $content.Substring($endOfMarker)
    } elseif ($s -ge 0) {
        $newContent = $content.Substring(0, $s) + $Section
    } elseif ($e -ge 0) {
        $endOfMarker = $e + $MarkerEnd.Length
        if ($endOfMarker -lt $content.Length -and $content[$endOfMarker] -eq "`r") { $endOfMarker++ }
        if ($endOfMarker -lt $content.Length -and $content[$endOfMarker] -eq "`n") { $endOfMarker++ }
        $newContent = $Section + $content.Substring($endOfMarker)
    } else {
        if ($content -and -not $content.EndsWith("`n")) { $content += "`n" }
        if ($content) { $newContent = $content + "`n" + $Section } else { $newContent = $Section }
    }
} else {
    $newContent = $Section
}

$newContent = $newContent.Replace("`r`n", "`n").Replace("`r", "`n")
[System.IO.File]::WriteAllText($CtxPath, $newContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "agent-context: updated $ContextFile"

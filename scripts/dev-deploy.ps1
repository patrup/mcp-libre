#Requires -Version 5.1
<#
.SYNOPSIS
    Dev-mode deploy: sync plugin/ to build/dev/ (fixing imports) and create
    a junction in LO share/extensions/ so changes take effect on LO restart.
    No unopkg needed. Run as Admin the first time (for the junction).

.EXAMPLE
    .\dev-deploy.ps1          # Sync files + create junction if missing
    .\dev-deploy.ps1 -Remove  # Remove the junction
#>

[CmdletBinding()]
param(
    [switch]$Remove
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path $PSScriptRoot
$PluginDir   = Join-Path $ProjectRoot "plugin"
$DevDir      = Join-Path $ProjectRoot "build\dev"
$ExtName     = "mcp-libre"

# Find LO extensions dir
$LOExtDir = $null
foreach ($p in @(
    "${env:ProgramFiles}\LibreOffice\share\extensions",
    "${env:ProgramFiles(x86)}\LibreOffice\share\extensions",
    "C:\Program Files\LibreOffice\share\extensions"
)) {
    if (Test-Path $p) { $LOExtDir = $p; break }
}

if (-not $LOExtDir) {
    Write-Host "[X] LibreOffice share/extensions not found" -ForegroundColor Red
    exit 1
}

$JunctionPath = Join-Path $LOExtDir $ExtName

# ── Remove mode ──────────────────────────────────────────────────────────────

if ($Remove) {
    if (Test-Path $JunctionPath) {
        cmd /c "rmdir `"$JunctionPath`"" 2>$null
        Write-Host "[OK] Junction removed: $JunctionPath" -ForegroundColor Green
    } else {
        Write-Host "[OK] No junction to remove" -ForegroundColor Gray
    }
    exit 0
}

# ── Helper ───────────────────────────────────────────────────────────────────

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

# ── Sync plugin/ → build/dev/ (with import fixes) ───────────────────────────

Write-Host ""
Write-Host "=== Dev Deploy ===" -ForegroundColor Cyan
Write-Host ""

# Clean and recreate dev dir
if (Test-Path $DevDir) { Remove-Item $DevDir -Recurse -Force }
New-Item -ItemType Directory -Path $DevDir -Force | Out-Null

# registration.py → root (UNO component entry point)
Copy-Item (Join-Path $PluginDir "pythonpath\registration.py") $DevDir

# pythonpath/ — helper modules
$devPy = Join-Path $DevDir "pythonpath"
New-Item -ItemType Directory -Path $devPy -Force | Out-Null
foreach ($f in @("uno_bridge.py", "mcp_server.py", "ai_interface.py", "main_thread_executor.py", "version.py")) {
    Copy-Item (Join-Path $PluginDir "pythonpath\$f") $devPy
}

# Fix relative imports in all .py files
Get-ChildItem $DevDir -Filter "*.py" -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -Encoding UTF8
    $content = $content -replace '^\xEF\xBB\xBF', ''
    $content = $content.TrimStart([char]0xFEFF)
    $original = $content
    $content = $content -replace 'from \.([\w]+) import', 'from $1 import'
    $content = $content -replace 'import \.([\w]+)', 'import $1'
    Write-Utf8NoBom $_.FullName $content
    if ($content -ne $original) {
        Write-Host "    Fixed imports: $($_.Name)" -ForegroundColor Gray
    }
}

# AGENT.md (served by HTTP endpoint)
Copy-Item (Join-Path $ProjectRoot "AGENT.md") $DevDir

# XCU/XCS config files
foreach ($f in @("Addons.xcu", "ProtocolHandler.xcu", "MCPServerConfig.xcs", "MCPServerConfig.xcu", "OptionsDialog.xcu", "Jobs.xcu")) {
    Copy-Item (Join-Path $PluginDir $f) $DevDir
}

# Dialogs
$devDialogs = Join-Path $DevDir "dialogs"
New-Item -ItemType Directory -Path $devDialogs -Force | Out-Null
Copy-Item (Join-Path $PluginDir "dialogs\MCPSettings.xdl") $devDialogs

# Icons
$devIcons = Join-Path $DevDir "icons"
New-Item -ItemType Directory -Path $devIcons -Force | Out-Null
Copy-Item (Join-Path $PluginDir "icons\*.png") $devIcons

# META-INF/manifest.xml
$devMeta = Join-Path $DevDir "META-INF"
New-Item -ItemType Directory -Path $devMeta -Force | Out-Null

$manifestXml = @'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE manifest:manifest PUBLIC "-//OpenOffice.org//DTD Manifest 1.0//EN" "Manifest.dtd">
<manifest:manifest xmlns:manifest="http://openoffice.org/2001/manifest">
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.uno-component;type=Python" manifest:full-path="registration.py"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-schema" manifest:full-path="MCPServerConfig.xcs"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="MCPServerConfig.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="Addons.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="ProtocolHandler.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="OptionsDialog.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="Jobs.xcu"/>
</manifest:manifest>
'@
Write-Utf8NoBom (Join-Path $devMeta "manifest.xml") $manifestXml

# description.xml
# Read version from version.py (single source of truth)
$regContent = Get-Content (Join-Path $PluginDir "pythonpath\version.py") -Raw
$version = "0.0.0"
if ($regContent -match 'EXTENSION_VERSION\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
}

$descXml = @"
<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/description/2006"
             xmlns:xlink="http://www.w3.org/1999/xlink">
    <identifier value="org.mcp.libreoffice.extension"/>
    <version value="$version"/>
    <display-name>
        <name lang="en">LibreOffice MCP Server Extension</name>
    </display-name>
    <publisher>
        <name lang="en" xlink:href="https://github.com">MCP LibreOffice Team</name>
    </publisher>
</description>
"@
Write-Utf8NoBom (Join-Path $DevDir "description.xml") $descXml

$fileCount = (Get-ChildItem $DevDir -Recurse -File).Count
Write-Host "[OK] Synced $fileCount files to build\dev\ (v$version)" -ForegroundColor Green

# ── Create junction if missing ───────────────────────────────────────────────

if (Test-Path $JunctionPath) {
    # Check if it points to the right place
    $target = (Get-Item $JunctionPath).Target
    Write-Host "[OK] Junction exists: $JunctionPath" -ForegroundColor Green
} else {
    Write-Host "[*] Creating junction: $JunctionPath -> $DevDir" -ForegroundColor White
    cmd /c "mklink /J `"$JunctionPath`" `"$DevDir`""
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] Failed to create junction. Run as Administrator." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Junction created" -ForegroundColor Green
}

# ── Delete __pycache__ to avoid stale bytecode ───────────────────────────────

Get-ChildItem $DevDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

# ── Re-register bundled extensions (needed for Jobs.xcu / new components) ────

$unopkg = Join-Path (Split-Path $LOExtDir) "program\unopkg"
if (-not (Test-Path $unopkg)) {
    $unopkg = "C:\Program Files\LibreOffice\program\unopkg.exe"
}
if (Test-Path $unopkg) {
    # unopkg creates a user profile lock — make sure no LO is running
    Get-Process soffice*, soffice.bin -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1
    $ErrorActionPreference = "Continue"
    & $unopkg reinstall --bundled 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"
    # Clean up residual lock left by unopkg
    $lockFile = Join-Path $env:APPDATA "LibreOffice\4\user\.lock"
    if (Test-Path $lockFile) { Remove-Item $lockFile -Force }
    Write-Host "[OK] Bundled extensions re-registered (unopkg reinstall)" -ForegroundColor Green
} else {
    Write-Host "[!] unopkg not found, skip bundled reinstall" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "  Restart LibreOffice to load v$version" -ForegroundColor Gray
Write-Host "  Edit plugin/*.py, run .\scripts\dev-deploy.ps1, restart LO" -ForegroundColor Gray
Write-Host ""

#Requires -Version 5.1
<#
.SYNOPSIS
    One-click setup for mcp-libre on Windows.

.DESCRIPTION
    Installs all dependencies (Python 3.12+, LibreOffice, UV, optionally Node.js & Java),
    configures PATH, syncs Python packages, and generates Claude Desktop config.

    With -Plugin: builds and installs the LibreOffice extension (.oxt).

    Uses winget (built into Windows 10/11) - no need for Chocolatey.

.EXAMPLE
    .\install.ps1                  # Full environment setup
    .\install.ps1 -SkipOptional    # Skip optional dependencies
    .\install.ps1 -CheckOnly       # Only check status, don't install
    .\install.ps1 -Plugin          # Build + install LibreOffice extension
    .\install.ps1 -Plugin -Force   # Build + install (no prompts, kills LO)
    .\install.ps1 -BuildOnly       # Only build the .oxt, don't install
#>

[CmdletBinding()]
param(
    [switch]$SkipOptional,
    [switch]$CheckOnly,
    [switch]$Force,
    [switch]$Plugin,
    [switch]$BuildOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────

$Script:ProjectRoot = $PSScriptRoot
$Script:Errors = @()
$Script:Warnings = @()

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    Write-Host "[*] $Text" -ForegroundColor White
}

function Write-OK {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Text)
    Write-Host "[!!] $Text" -ForegroundColor Yellow
    $Script:Warnings += $Text
}

function Write-Err {
    param([string]$Text)
    Write-Host "[X] $Text" -ForegroundColor Red
    $Script:Errors += $Text
}

function Write-Info {
    param([string]$Text)
    Write-Host "    $Text" -ForegroundColor Gray
}

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Refresh-PathEnv {
    # Reload PATH from registry so newly-installed tools are found
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Add-ToUserPath {
    param([string]$Directory)
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$Directory*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$Directory", "User")
        $env:Path = "$env:Path;$Directory"
        Write-OK "Added to PATH: $Directory"
        return $true
    }
    return $false
}

# ── LibreOffice Detection ────────────────────────────────────────────────────

function Find-LibreOffice {
    # Check common installation paths on Windows
    $searchPaths = @(
        "${env:ProgramFiles}\LibreOffice\program",
        "${env:ProgramFiles(x86)}\LibreOffice\program",
        "${env:LOCALAPPDATA}\Programs\LibreOffice\program",
        "C:\Program Files\LibreOffice\program",
        "C:\Program Files (x86)\LibreOffice\program"
    )

    foreach ($p in $searchPaths) {
        $soffice = Join-Path $p "soffice.exe"
        if (Test-Path $soffice) {
            return $p
        }
    }

    # Also check if soffice is already in PATH
    $existing = Get-Command soffice -ErrorAction SilentlyContinue
    if ($existing) {
        return (Split-Path $existing.Source)
    }

    return $null
}

function Get-LibreOfficeVersion {
    param([string]$ProgramDir)
    try {
        $soffice = Join-Path $ProgramDir "soffice.exe"
        $output = & $soffice --version 2>&1 | Select-Object -First 1
        if ($output -match '(\d+\.\d+[\.\d]*)') {
            return $Matches[1]
        }
    } catch {}
    return $null
}

# ── Check / Install Functions ────────────────────────────────────────────────

function Test-Winget {
    if (Test-CommandExists "winget") {
        return $true
    }
    # winget might be available via App Installer
    $wingetPath = (Get-Command winget -ErrorAction SilentlyContinue)
    return $null -ne $wingetPath
}

function Install-WithWinget {
    param(
        [string]$PackageId,
        [string]$FriendlyName,
        [string[]]$ExtraArgs = @()
    )
    Write-Step "Installing $FriendlyName via winget..."
    $wingetArgs = @("install", "--id", $PackageId, "--accept-source-agreements", "--accept-package-agreements", "-e") + $ExtraArgs
    $process = Start-Process -FilePath "winget" -ArgumentList $wingetArgs -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -eq 0) {
        Write-OK "$FriendlyName installed successfully"
        Refresh-PathEnv
        return $true
    } else {
        Write-Warn "$FriendlyName install returned exit code $($process.ExitCode) (may already be installed or need restart)"
        Refresh-PathEnv
        return $false
    }
}

# ── 1. Python ────────────────────────────────────────────────────────────────

function Ensure-Python {
    Write-Header "Python 3.12+"

    # Check python or python3
    $pythonCmd = $null
    foreach ($cmd in @("python", "python3", "py")) {
        if (Test-CommandExists $cmd) {
            try {
                $ver = & $cmd --version 2>&1
                if ($ver -match 'Python (\d+)\.(\d+)') {
                    $major = [int]$Matches[1]
                    $minor = [int]$Matches[2]
                    if ($major -ge 3 -and $minor -ge 12) {
                        $pythonCmd = $cmd
                        Write-OK "Python found: $ver (command: $cmd)"
                        break
                    } else {
                        Write-Info "Found $ver via '$cmd' but need 3.12+"
                    }
                }
            } catch {}
        }
    }

    if ($pythonCmd) {
        return $pythonCmd
    }

    if ($CheckOnly) {
        Write-Err "Python 3.12+ not found"
        return $null
    }

    # Install via winget
    if (Test-Winget) {
        Install-WithWinget "Python.Python.3.12" "Python 3.12"
        # Refresh and re-check
        Refresh-PathEnv
        foreach ($cmd in @("python", "python3", "py")) {
            if (Test-CommandExists $cmd) {
                $ver = & $cmd --version 2>&1
                if ($ver -match 'Python 3\.1[2-9]') {
                    Write-OK "Python verified after install: $ver"
                    return $cmd
                }
            }
        }
    }

    Write-Err "Could not install Python. Please install manually from https://www.python.org/downloads/"
    Write-Info "Make sure to check 'Add Python to PATH' during installation!"
    return $null
}

# ── 2. LibreOffice ───────────────────────────────────────────────────────────

function Ensure-LibreOffice {
    Write-Header "LibreOffice 24.2+"

    $loDir = Find-LibreOffice
    if ($loDir) {
        $version = Get-LibreOfficeVersion $loDir
        Write-OK "LibreOffice found at: $loDir"
        if ($version) {
            Write-OK "Version: $version"
            if ($version -match '^(\d+)' -and [int]$Matches[1] -lt 24) {
                Write-Warn "Version $version may be too old. Recommended: 24.2+"
            }
        }

        # Ensure soffice is in PATH
        if (-not (Test-CommandExists "soffice")) {
            if (-not $CheckOnly) {
                Add-ToUserPath $loDir
                Write-OK "Added LibreOffice program directory to PATH"
            } else {
                Write-Warn "LibreOffice program directory NOT in PATH: $loDir"
                Write-Info "The setup script will add it automatically when run without -CheckOnly"
            }
        } else {
            Write-OK "soffice.exe is in PATH"
        }
        return $loDir
    }

    if ($CheckOnly) {
        Write-Err "LibreOffice not found"
        return $null
    }

    # Install via winget
    if (Test-Winget) {
        Install-WithWinget "TheDocumentFoundation.LibreOffice" "LibreOffice"
        Refresh-PathEnv

        $loDir = Find-LibreOffice
        if ($loDir) {
            Add-ToUserPath $loDir
            Write-OK "LibreOffice installed and PATH configured"
            return $loDir
        }
    }

    Write-Err "Could not install LibreOffice. Please install manually from https://www.libreoffice.org/download/"
    return $null
}

# ── 3. UV Package Manager ───────────────────────────────────────────────────

function Ensure-UV {
    Write-Header "UV Package Manager"

    if (Test-CommandExists "uv") {
        $uvVer = & uv --version 2>&1 | Select-Object -First 1
        Write-OK "UV found: $uvVer"
        return $true
    }

    if ($CheckOnly) {
        Write-Err "UV not found"
        return $false
    }

    # Install UV via the official installer
    Write-Step "Installing UV..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        Refresh-PathEnv

        if (Test-CommandExists "uv") {
            $uvVer = & uv --version 2>&1 | Select-Object -First 1
            Write-OK "UV installed: $uvVer"
            return $true
        }

        # UV installs to ~/.local/bin or ~/.cargo/bin usually
        $uvPaths = @(
            "$env:USERPROFILE\.local\bin",
            "$env:USERPROFILE\.cargo\bin",
            "$env:LOCALAPPDATA\uv"
        )
        foreach ($p in $uvPaths) {
            if (Test-Path (Join-Path $p "uv.exe")) {
                Add-ToUserPath $p
                Write-OK "UV installed at: $p"
                return $true
            }
        }
    } catch {
        Write-Warn "UV installer script failed: $_"
    }

    # Fallback: try winget
    if (Test-Winget) {
        Install-WithWinget "astral-sh.uv" "UV"
        Refresh-PathEnv
        if (Test-CommandExists "uv") {
            Write-OK "UV installed via winget"
            return $true
        }
    }

    Write-Err "Could not install UV. Try: pip install uv  or  winget install astral-sh.uv"
    return $false
}

# ── 4. Node.js (Optional) ───────────────────────────────────────────────────

function Ensure-NodeJS {
    Write-Header "Node.js 18+ (optional - Super Assistant proxy)"

    if (Test-CommandExists "node") {
        $nodeVer = & node --version 2>&1
        Write-OK "Node.js found: $nodeVer"
        return $true
    }

    if ($SkipOptional -or $CheckOnly) {
        Write-Warn "Node.js not found (optional - needed for Super Assistant Chrome extension)"
        return $false
    }

    if (Test-Winget) {
        Install-WithWinget "OpenJS.NodeJS.LTS" "Node.js LTS"
        Refresh-PathEnv
        if (Test-CommandExists "node") {
            Write-OK "Node.js installed"
            return $true
        }
    }

    Write-Warn "Could not install Node.js. Install manually from https://nodejs.org/"
    return $false
}

# ── 5. Java (Optional) ──────────────────────────────────────────────────────

function Ensure-Java {
    Write-Header "Java Runtime (optional - advanced LibreOffice features)"

    if (Test-CommandExists "java") {
        $javaVer = & java -version 2>&1 | Select-Object -First 1
        Write-OK "Java found: $javaVer"
        return $true
    }

    if ($SkipOptional -or $CheckOnly) {
        Write-Warn "Java not found (optional - some LibreOffice features may be limited)"
        return $false
    }

    if (Test-Winget) {
        Install-WithWinget "EclipseAdoptium.Temurin.21.JRE" "Eclipse Temurin JRE 21"
        Refresh-PathEnv
        if (Test-CommandExists "java") {
            Write-OK "Java installed"
            return $true
        }
    }

    Write-Warn "Could not install Java. Install manually from https://adoptium.net/"
    return $false
}

# ── 6. Project Setup ────────────────────────────────────────────────────────

function Initialize-Project {
    Write-Header "Project Dependencies (uv sync)"

    Push-Location $Script:ProjectRoot
    try {
        Write-Step "Running uv sync to install Python dependencies..."
        & uv sync 2>&1 | ForEach-Object { Write-Info $_ }
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Python dependencies installed"
        } else {
            Write-Err "uv sync failed (exit code $LASTEXITCODE)"
        }
    } finally {
        Pop-Location
    }
}

# ── 7. Claude MCP Configuration ──────────────────────────────────────────────

function Get-McpEntry {
    $projectPath = $Script:ProjectRoot -replace '\\', '/'
    $uvPath = (Get-Command uv -ErrorAction SilentlyContinue).Source
    if (-not $uvPath) { $uvPath = "uv" }
    $uvPath = $uvPath -replace '\\', '/'

    return @{
        command = $uvPath
        args = @("run", "python", "src/main.py")
        cwd = $projectPath
        env = @{
            PYTHONPATH = "$projectPath/src"
        }
    }
}

function Add-McpToJsonFile {
    param(
        [string]$ConfigFile,
        [string]$Label,
        [hashtable]$McpEntry
    )

    if (-not (Test-Path $ConfigFile)) {
        return $false
    }

    Write-Step "$Label config found: $ConfigFile"
    try {
        # Backup before any modification
        $bakFile = "$ConfigFile.bak"
        Copy-Item $ConfigFile $bakFile -Force
        Write-Info "Backup saved: $bakFile"

        $raw = Get-Content $ConfigFile -Raw -Encoding UTF8
        $config = $raw | ConvertFrom-Json

        # Ensure mcpServers object exists
        if (-not $config.PSObject.Properties['mcpServers']) {
            $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
        }

        # Remove ALL old libreoffice entries (libreoffice, libreoffice-server, etc.)
        $staleKeys = @($config.mcpServers.PSObject.Properties | Where-Object { $_.Name -match 'libreoffice' } | ForEach-Object { $_.Name })
        foreach ($key in $staleKeys) {
            Write-Warn ($Label + ": Removing old entry '$key'")
            $config.mcpServers.PSObject.Properties.Remove($key)
        }

        # Add the new entry
        $config.mcpServers | Add-Member -MemberType NoteProperty -Name "libreoffice" -Value ([PSCustomObject]$McpEntry) -Force
        $config | ConvertTo-Json -Depth 10 | Set-Content $ConfigFile -Encoding UTF8
        Write-OK ($Label + ": MCP server 'libreoffice' configured")
        return $true
    } catch {
        Write-Warn ($Label + ": Could not update config: $_")
        # Restore backup on failure
        if (Test-Path "$ConfigFile.bak") {
            Copy-Item "$ConfigFile.bak" $ConfigFile -Force
            Write-Info "Restored from backup after error"
        }
        return $false
    }
}

function Set-ClaudeConfig {
    Write-Header "Claude MCP Configuration"

    $mcpEntry = Get-McpEntry

    # ── Detect Claude Desktop ────────────────────────────────────────────
    $desktopDir = "$env:APPDATA\Claude"
    $desktopConfig = "$desktopDir\claude_desktop_config.json"
    $desktopInstalled = (Test-Path $desktopDir) -and (
        (Test-Path "$desktopDir\config.json") -or
        (Test-Path "$desktopDir\window-state.json") -or
        (Test-Path "$env:LOCALAPPDATA\Programs\Claude")
    )

    if ($desktopInstalled) {
        Write-OK "Claude Desktop detected"
        if (-not (Test-Path $desktopConfig)) {
            $config = @{
                mcpServers = @{
                    libreoffice = $mcpEntry
                }
            }
            $config | ConvertTo-Json -Depth 10 | Set-Content $desktopConfig -Encoding UTF8
            Write-OK "Claude Desktop: Created config with MCP server 'libreoffice'"
        } else {
            Add-McpToJsonFile -ConfigFile $desktopConfig -Label "Claude Desktop" -McpEntry $mcpEntry | Out-Null
        }
        Write-Info "Restart Claude Desktop to pick up changes."
    } else {
        Write-Warn "Claude Desktop not detected"
        Write-Info "Install Claude Desktop, then re-run this script."
        Write-Info "Or configure manually - see docs/WINDOWS_SETUP.md"
    }
}

# ── 8. Verification ─────────────────────────────────────────────────────────

function Test-Setup {
    Write-Header "Verification"

    $allOk = $true

    # Python
    Write-Step "Checking Python..."
    if (Test-CommandExists "python") {
        $ver = & python --version 2>&1
        Write-OK "Python: $ver"
    } elseif (Test-CommandExists "python3") {
        $ver = & python3 --version 2>&1
        Write-OK "Python: $ver"
    } else {
        Write-Err "Python NOT found in PATH"
        $allOk = $false
    }

    # LibreOffice / soffice
    Write-Step "Checking LibreOffice (soffice)..."
    if (Test-CommandExists "soffice") {
        $ver = & soffice --version 2>&1 | Select-Object -First 1
        Write-OK "LibreOffice: $ver"
    } else {
        $loDir = Find-LibreOffice
        if ($loDir) {
            Write-Warn "LibreOffice installed at $loDir but NOT in PATH"
            Write-Info "Restart your terminal or run:  `$env:Path += ';$loDir'"
        } else {
            Write-Err "LibreOffice NOT found"
        }
        $allOk = $false
    }

    # UV
    Write-Step "Checking UV..."
    if (Test-CommandExists "uv") {
        $ver = & uv --version 2>&1 | Select-Object -First 1
        Write-OK "UV: $ver"
    } else {
        Write-Err "UV NOT found in PATH"
        $allOk = $false
    }

    # MCP server quick test
    Write-Step "Testing MCP server import..."
    Push-Location $Script:ProjectRoot
    try {
        $testResult = & uv run python -c "from src.libremcp import mcp; print('MCP server OK')" 2>&1
        if ($testResult -match "MCP server OK") {
            Write-OK "MCP server module loads correctly"
        } else {
            Write-Warn "MCP server import issue: $testResult"
        }
    } catch {
        Write-Warn "Could not test MCP server: $_"
    } finally {
        Pop-Location
    }

    # Summary
    Write-Host ""
    if ($allOk) {
        Write-OK "All required dependencies are installed and configured!"
    } else {
        Write-Err "Some dependencies are missing. You may need to restart your terminal."
    }

    return $allOk
}

# ── Main ─────────────────────────────────────────────────────────────────────

function Main {
    # ── Plugin mode: delegate to scripts/install-plugin.ps1 ──────────────
    if ($Plugin -or $BuildOnly) {
        $pluginScript = Join-Path $Script:ProjectRoot "scripts\install-plugin.ps1"
        if (-not (Test-Path $pluginScript)) {
            Write-Err "scripts\install-plugin.ps1 not found"
            exit 1
        }
        $pluginArgs = @()
        if ($BuildOnly) { $pluginArgs += "-BuildOnly" }
        if ($Force)     { $pluginArgs += "-Force" }
        & $pluginScript @pluginArgs
        return
    }

    Write-Header "mcp-libre Windows Setup"

    if (-not (Test-IsAdmin)) {
        Write-Warn "Not running as Administrator. Some installs may require elevation."
        Write-Info "Tip: Right-click PowerShell -> 'Run as administrator' for best results."
        Write-Host ""
    }

    if (-not (Test-Winget)) {
        Write-Err "winget not found! It should be pre-installed on Windows 10/11."
        Write-Info "Install 'App Installer' from the Microsoft Store, then retry."
        if ($CheckOnly) { return }
        exit 1
    }
    Write-OK "winget is available"

    # Required dependencies
    $pythonCmd = Ensure-Python
    $loDir = Ensure-LibreOffice
    $uvOk = Ensure-UV

    # Optional dependencies
    if (-not $SkipOptional) {
        Ensure-NodeJS
        Ensure-Java
    }

    if ($CheckOnly) {
        Write-Header "Check Complete"
        Test-Setup | Out-Null
        return
    }

    # Project setup (only if all required deps are OK)
    if ($pythonCmd -and $loDir -and $uvOk) {
        Initialize-Project
        Set-ClaudeConfig
    } else {
        Write-Err "Cannot proceed with project setup: missing required dependencies."
        Write-Info "Fix the issues above and re-run this script."
        return
    }

    # Final verification
    Test-Setup | Out-Null

    # Summary
    Write-Header "Setup Complete!"
    Write-Host "  Next steps:" -ForegroundColor White
    Write-Host "  1. Restart your terminal (to pick up PATH changes)" -ForegroundColor Gray
    Write-Host "  2. Restart Claude Desktop (to load MCP server config)" -ForegroundColor Gray
    Write-Host "  3. Test: uv run python src/main.py --test" -ForegroundColor Gray
    Write-Host ""

    if ($Script:Warnings.Count -gt 0) {
        Write-Host "  Warnings:" -ForegroundColor Yellow
        $Script:Warnings | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
        Write-Host ""
    }
}

Main

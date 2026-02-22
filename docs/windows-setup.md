# Windows Setup

Installation and usage guide for mcp-libre on Windows.

## Quick Install

```powershell
# From PowerShell (admin recommended for winget installs)
cd mcp-libre
.\install.ps1
```

The script handles everything automatically:
1. Installs Python 3.12+, LibreOffice, UV via **winget** (built into Windows 10/11)
2. Adds `LibreOffice\program` to user PATH
3. Runs `uv sync` for Python dependencies
4. Configures Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)
5. Verifies the setup

### Script Options

| Option | Description |
|--------|-------------|
| `-CheckOnly` | Check status without installing anything |
| `-SkipOptional` | Skip Node.js and Java (optional deps) |
| `-Force` | Force reinstallation |

```powershell
# Dry run — see what's missing
.\install.ps1 -CheckOnly

# Install without Node.js or Java
.\install.ps1 -SkipOptional
```

## Manual Installation

If you prefer installing dependencies yourself:

### 1. Python 3.12+

```powershell
winget install Python.Python.3.12
```

Or from [python.org](https://www.python.org/downloads/) — check **"Add Python to PATH"** during installation.

### 2. LibreOffice 24.2+

```powershell
winget install TheDocumentFoundation.LibreOffice
```

Or from [libreoffice.org](https://www.libreoffice.org/download/).

After installation, add LibreOffice to PATH:

```powershell
# Add to user PATH (permanent)
$loPath = "C:\Program Files\LibreOffice\program"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$currentPath;$loPath", "User")
```

Verify:

```powershell
# Restart your terminal, then:
soffice --version
```

### 3. UV

```powershell
# Official installer
irm https://astral.sh/uv/install.ps1 | iex

# Or via winget
winget install astral-sh.uv
```

### 4. Python Dependencies

```powershell
cd mcp-libre
uv sync
```

### 5. Optional: Node.js, Java

```powershell
winget install OpenJS.NodeJS.LTS              # For Super Assistant proxy
winget install EclipseAdoptium.Temurin.21.JRE  # For advanced LibreOffice features
```

## Claude Desktop Configuration

The `install.ps1` script generates this automatically.

To configure manually, create/edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "uv",
      "args": ["run", "python", "src/main.py"],
      "cwd": "C:/Users/YOUR_NAME/mcp/mcp-libre",
      "env": {
        "PYTHONPATH": "C:/Users/YOUR_NAME/mcp/mcp-libre/src"
      }
    }
  }
}
```

Restart Claude Desktop after editing.

## Verification

```powershell
# Check dependencies
python --version          # 3.12+
soffice --version         # LibreOffice 24.2+
uv --version

# Test the MCP server
cd mcp-libre
uv run python src/main.py --test
```

## Troubleshooting

### "soffice" is not recognized

LibreOffice is not in PATH:

```powershell
# Find where LibreOffice is installed
Get-ChildItem "C:\Program Files" -Filter "soffice.exe" -Recurse -ErrorAction SilentlyContinue

# Add to PATH (adjust path if needed)
$loPath = "C:\Program Files\LibreOffice\program"
[Environment]::SetEnvironmentVariable("Path", "$env:Path;$loPath", "User")
```

Restart your terminal.

### Python is not recognized

The Microsoft Store intercepts the `python` command. Disable in:
**Settings > Apps > App execution aliases** — turn off the Python aliases.

Or use `py` instead:

```powershell
py --version
```

### Black console window flashing during conversions

Normal on Windows when LibreOffice runs in headless mode. The code already includes a fix (`STARTUPINFO` with `SW_HIDE`) to suppress these windows.

### uv sync fails

```powershell
# Check that uv is in PATH
uv --version

# If not found, restart terminal or add manually
$env:Path += ";$env:USERPROFILE\.local\bin"
```

### winget permission errors

Relaunch PowerShell as administrator:
right-click PowerShell > **Run as administrator**.

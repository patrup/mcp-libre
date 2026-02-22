# LibreOffice MCP Server - Prerequisites Quick Reference

## ✅ Required Components

### 1. LibreOffice 24.2+
- **Purpose**: Document processing engine
- **Ubuntu/Debian**: `sudo apt install libreoffice`
- **CentOS/RHEL**: `sudo yum install libreoffice` 
- **macOS**: `brew install --cask libreoffice`
- **Windows**: [Download from libreoffice.org](https://www.libreoffice.org/download/)

### 2. Python 3.12+
- **Purpose**: Runtime environment for MCP server
- **Ubuntu/Debian**: `sudo apt install python3.12 python3.12-venv`
- **macOS**: `brew install python@3.12`
- **Windows**: [Download from python.org](https://www.python.org/downloads/)

### 3. UV Package Manager
- **Purpose**: Fast Python package management
- **All Platforms**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Alternative**: `pip install uv`

## 🔧 Optional Components

### 4. Node.js 18+ & NPM
- **Purpose**: Super Assistant Chrome extension proxy
- **Ubuntu/Debian**: `sudo apt install nodejs npm`
- **macOS**: `brew install node`
- **Windows**: [Download from nodejs.org](https://nodejs.org/)

### 5. Java Runtime Environment (JRE 11+)
- **Purpose**: Advanced LibreOffice features (PDF generation)
- **Ubuntu/Debian**: `sudo apt install default-jre`
- **macOS**: `brew install openjdk`
- **Windows**: [Download from adoptium.net](https://adoptium.net/)

## 🚀 Quick Setup Commands

### Ubuntu/Debian
```bash
# Required components
sudo apt update
sudo apt install libreoffice python3.12 python3.12-venv curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Optional components
sudo apt install nodejs npm default-jre
```

### macOS (with Homebrew)
```bash
# Required components
brew install --cask libreoffice
brew install python@3.12
curl -LsSf https://astral.sh/uv/install.sh | sh

# Optional components
brew install node openjdk
```

### Windows

```powershell
# Automatic (recommended):
.\install.ps1

# Or manually via winget:
winget install Python.Python.3.12
winget install TheDocumentFoundation.LibreOffice
irm https://astral.sh/uv/install.ps1 | iex

# Optional:
winget install OpenJS.NodeJS.LTS
winget install EclipseAdoptium.Temurin.21.JRE
```

See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for the full guide.

## 🔍 Verification Commands

```bash
# Check LibreOffice
libreoffice --version
libreoffice --headless --help

# Check Python
python3 --version
python3 -c "import sys; print('✓ Python 3.12+' if sys.version_info >= (3, 12) else '✗ Need Python 3.12+')"

# Check UV
uv --version

# Check Node.js (optional)
node --version
npm --version

# Check Java (optional)
java -version
```

## 🛠 Helper Script

Use the included helper script for automated checking:

```bash
# Show detailed requirements
./mcp-helper.sh requirements

# Check your system
./mcp-helper.sh check

# Test functionality
./mcp-helper.sh test
```

## 💾 System Requirements

- **OS**: Linux, macOS, Windows
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet access for initial setup only

## 🔗 Integration Support

- **Claude Desktop**: Direct MCP protocol
- **Super Assistant**: Chrome extension via proxy
- **Custom Clients**: Python FastMCP framework

---

For the most up-to-date installation instructions, run `./mcp-helper.sh requirements`

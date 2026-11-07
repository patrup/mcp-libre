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

## 🚀 Quick Setup Commands

### Ubuntu/Debian
```bash
# Required components
sudo apt update
sudo apt install libreoffice python3.12 python3.12-venv curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Optional components
sudo apt install nodejs npm
```

### macOS (with Homebrew)
```bash
# Required components
brew install --cask libreoffice
brew install python@3.12
curl -LsSf https://astral.sh/uv/install.sh | sh

# Optional components
brew install node
```

### Windows (with Chocolatey)
```bash
# Required components
choco install libreoffice python312
# Then install UV manually from the website

# Optional components
choco install nodejs
```

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

```

## 🛠 Helper Script

Use the included helper script for automated checking:

```bash
# Show detailed requirements
./mcp-helper.sh requirements

# Check your system
./mcp-helper.sh check

# Run automated tests
uv run pytest -q

# Exercise the real stdio transport
uv run pytest -q tests/test_stdio_protocol.py

# Run the LibreOffice smoke test (keeps artifacts in test-output/)
uv run python src/main.py --test
```

## 💾 System Requirements

- **OS**: Linux, macOS, Windows
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet access for initial setup only

## 🔗 Integration Support

- **Claude Desktop**: Direct MCP protocol
- **Super Assistant**: Chrome extension via proxy
- **Custom Clients**: Python MCP SDK

---

For the most up-to-date installation instructions, run `./mcp-helper.sh requirements`

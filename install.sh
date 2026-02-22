#!/bin/bash
# One-click setup for mcp-libre on Linux.
#
# Checks/installs all dependencies (Python 3.12+, LibreOffice, UV, optionally
# Node.js & Java), syncs Python packages, and generates Claude Desktop config.
#
# Usage:
#   ./install.sh                 # Full environment setup
#   ./install.sh --skip-optional # Skip optional dependencies
#   ./install.sh --check-only   # Only check status, don't install
#   ./install.sh --plugin       # Build + install LibreOffice extension
#   ./install.sh --plugin --force
#   ./install.sh --build-only   # Only build the .oxt, don't install

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Parse args
SKIP_OPTIONAL=false
CHECK_ONLY=false
PLUGIN=false
BUILD_ONLY=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --skip-optional) SKIP_OPTIONAL=true ;;
        --check-only)    CHECK_ONLY=true ;;
        --plugin)        PLUGIN=true ;;
        --build-only)    BUILD_ONLY=true ;;
        --force)         FORCE=true ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-optional  Skip optional dependencies (Node.js, Java)"
            echo "  --check-only     Only check status, don't install"
            echo "  --plugin         Build + install LibreOffice extension"
            echo "  --plugin --force Build + install (no prompts, kills LO)"
            echo "  --build-only     Only build the .oxt, don't install"
            exit 0
            ;;
    esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────

ERRORS=()
WARNINGS=()

write_header() { echo ""; echo "========================================"; echo "  $1"; echo "========================================"; echo ""; }
write_step()   { echo "[*] $1"; }
write_ok()     { echo "[OK] $1"; }
write_warn()   { echo "[!!] $1"; WARNINGS+=("$1"); }
write_err()    { echo "[X] $1"; ERRORS+=("$1"); }
write_info()   { echo "    $1"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# ── Detect package manager ──────────────────────────────────────────────────

detect_pkg_manager() {
    if command_exists apt; then echo "apt"
    elif command_exists dnf; then echo "dnf"
    elif command_exists yum; then echo "yum"
    elif command_exists pacman; then echo "pacman"
    elif command_exists zypper; then echo "zypper"
    elif command_exists brew; then echo "brew"
    else echo "unknown"
    fi
}

PKG_MANAGER=$(detect_pkg_manager)

# ── 1. Python 3.12+ ─────────────────────────────────────────────────────────

ensure_python() {
    write_header "Python 3.12+"

    local python_cmd=""
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            local ver
            ver=$($cmd --version 2>&1)
            if echo "$ver" | grep -qP 'Python 3\.(1[2-9]|[2-9]\d)'; then
                python_cmd="$cmd"
                write_ok "Python found: $ver (command: $cmd)"
                break
            else
                write_info "Found $ver via '$cmd' but need 3.12+"
            fi
        fi
    done

    if [ -n "$python_cmd" ]; then
        PYTHON_CMD="$python_cmd"
        return 0
    fi

    if $CHECK_ONLY; then
        write_err "Python 3.12+ not found"
        return 1
    fi

    write_step "Installing Python..."
    case "$PKG_MANAGER" in
        apt)    sudo apt update && sudo apt install -y python3 python3-venv ;;
        dnf)    sudo dnf install -y python3 ;;
        pacman) sudo pacman -S --noconfirm python ;;
        brew)   brew install python@3.12 ;;
        *)      write_err "Cannot auto-install Python. Install Python 3.12+ manually."; return 1 ;;
    esac

    for cmd in python3 python; do
        if command_exists "$cmd"; then
            local ver
            ver=$($cmd --version 2>&1)
            if echo "$ver" | grep -qP 'Python 3\.(1[2-9]|[2-9]\d)'; then
                PYTHON_CMD="$cmd"
                write_ok "Python installed: $ver"
                return 0
            fi
        fi
    done

    write_err "Could not install Python 3.12+. Please install manually."
    return 1
}

# ── 2. LibreOffice ──────────────────────────────────────────────────────────

ensure_libreoffice() {
    write_header "LibreOffice 24.2+"

    if command_exists soffice; then
        local ver
        ver=$(soffice --version 2>&1 | head -1)
        write_ok "LibreOffice found: $ver"
        return 0
    fi

    # Check common paths
    for candidate in \
        /usr/lib/libreoffice/program/soffice \
        /opt/libreoffice*/program/soffice \
        /snap/bin/libreoffice; do
        for c in $candidate; do
            if [ -x "$c" ]; then
                write_ok "LibreOffice found at: $c"
                write_warn "soffice is not in PATH. Add its directory to PATH."
                return 0
            fi
        done
    done

    if $CHECK_ONLY; then
        write_err "LibreOffice not found"
        return 1
    fi

    write_step "Installing LibreOffice..."
    case "$PKG_MANAGER" in
        apt)    sudo apt update && sudo apt install -y libreoffice ;;
        dnf)    sudo dnf install -y libreoffice ;;
        pacman) sudo pacman -S --noconfirm libreoffice-fresh ;;
        brew)   brew install --cask libreoffice ;;
        *)      write_err "Cannot auto-install LibreOffice. Install manually from https://www.libreoffice.org/download/"; return 1 ;;
    esac

    if command_exists soffice; then
        write_ok "LibreOffice installed"
        return 0
    fi

    write_err "Could not install LibreOffice. Please install manually."
    return 1
}

# ── 3. UV Package Manager ──────────────────────────────────────────────────

ensure_uv() {
    write_header "UV Package Manager"

    if command_exists uv; then
        local ver
        ver=$(uv --version 2>&1 | head -1)
        write_ok "UV found: $ver"
        return 0
    fi

    if $CHECK_ONLY; then
        write_err "UV not found"
        return 1
    fi

    write_step "Installing UV..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        # Reload PATH
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        if command_exists uv; then
            write_ok "UV installed: $(uv --version 2>&1 | head -1)"
            return 0
        fi
    fi

    write_err "Could not install UV. Try: curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 1
}

# ── 4. Node.js (Optional) ──────────────────────────────────────────────────

ensure_nodejs() {
    write_header "Node.js 18+ (optional - Super Assistant proxy)"

    if command_exists node; then
        write_ok "Node.js found: $(node --version 2>&1)"
        return 0
    fi

    if $SKIP_OPTIONAL || $CHECK_ONLY; then
        write_warn "Node.js not found (optional - needed for Super Assistant)"
        return 0
    fi

    write_step "Installing Node.js..."
    case "$PKG_MANAGER" in
        apt)    sudo apt install -y nodejs npm ;;
        dnf)    sudo dnf install -y nodejs npm ;;
        pacman) sudo pacman -S --noconfirm nodejs npm ;;
        brew)   brew install node ;;
        *)      write_warn "Cannot auto-install Node.js. Install from https://nodejs.org/"; return 0 ;;
    esac

    if command_exists node; then
        write_ok "Node.js installed: $(node --version 2>&1)"
    else
        write_warn "Could not install Node.js (optional)"
    fi
}

# ── 5. Java (Optional) ─────────────────────────────────────────────────────

ensure_java() {
    write_header "Java Runtime (optional - advanced LibreOffice features)"

    if command_exists java; then
        write_ok "Java found: $(java -version 2>&1 | head -1)"
        return 0
    fi

    if $SKIP_OPTIONAL || $CHECK_ONLY; then
        write_warn "Java not found (optional - some LibreOffice features may be limited)"
        return 0
    fi

    write_step "Installing Java..."
    case "$PKG_MANAGER" in
        apt)    sudo apt install -y default-jre ;;
        dnf)    sudo dnf install -y java-latest-openjdk ;;
        pacman) sudo pacman -S --noconfirm jre-openjdk ;;
        brew)   brew install openjdk ;;
        *)      write_warn "Cannot auto-install Java. Install from https://adoptium.net/"; return 0 ;;
    esac

    if command_exists java; then
        write_ok "Java installed"
    else
        write_warn "Could not install Java (optional)"
    fi
}

# ── 6. Project Setup ───────────────────────────────────────────────────────

initialize_project() {
    write_header "Project Dependencies (uv sync)"

    write_step "Running uv sync to install Python dependencies..."
    (cd "$PROJECT_ROOT" && uv sync 2>&1 | while IFS= read -r line; do write_info "$line"; done)
    write_ok "Python dependencies installed"
}

# ── 7. Claude MCP Configuration ───────────────────────────────────────────

setup_claude_config() {
    write_header "Claude MCP Configuration"

    local project_path="$PROJECT_ROOT"
    local uv_path
    uv_path=$(command -v uv)

    # Claude Desktop config
    local claude_dir="$HOME/.config/claude"
    local claude_config="$claude_dir/claude_desktop_config.json"

    if [ -d "$claude_dir" ]; then
        write_ok "Claude Desktop config directory found"

        # Backup if exists
        if [ -f "$claude_config" ]; then
            cp "$claude_config" "$claude_config.bak"
            write_info "Backup saved: $claude_config.bak"

            # Check if libreoffice entry already exists
            if grep -q '"libreoffice"' "$claude_config" 2>/dev/null; then
                write_info "libreoffice entry already present in Claude config"
                return 0
            fi
        fi

        # Generate config with libreoffice MCP entry
        if [ -f "$claude_config" ] && command_exists jq; then
            # Merge into existing config using jq
            local tmp
            tmp=$(mktemp)
            jq --arg uv "$uv_path" --arg cwd "$project_path" \
                '.mcpServers.libreoffice = {
                    "command": $uv,
                    "args": ["run", "python", "src/main.py"],
                    "cwd": $cwd,
                    "env": {"PYTHONPATH": ($cwd + "/src")}
                }' "$claude_config" > "$tmp" && mv "$tmp" "$claude_config"
            write_ok "Claude Desktop: MCP server 'libreoffice' configured"
        else
            # Create new config
            mkdir -p "$claude_dir"
            cat > "$claude_config" << CLAUDE_EOF
{
  "mcpServers": {
    "libreoffice": {
      "command": "$uv_path",
      "args": ["run", "python", "src/main.py"],
      "cwd": "$project_path",
      "env": {
        "PYTHONPATH": "$project_path/src"
      }
    }
  }
}
CLAUDE_EOF
            write_ok "Claude Desktop: Created config with MCP server 'libreoffice'"
        fi
        write_info "Restart Claude Desktop to pick up changes."
    else
        write_warn "Claude Desktop config directory not found ($claude_dir)"
        write_info "Install Claude Desktop, then re-run this script."
    fi
}

# ── 8. Verification ────────────────────────────────────────────────────────

verify_setup() {
    write_header "Verification"

    local all_ok=true

    write_step "Checking Python..."
    if command_exists python3; then
        write_ok "Python: $(python3 --version 2>&1)"
    else
        write_err "Python NOT found in PATH"
        all_ok=false
    fi

    write_step "Checking LibreOffice..."
    if command_exists soffice; then
        write_ok "LibreOffice: $(soffice --version 2>&1 | head -1)"
    else
        write_err "soffice NOT found in PATH"
        all_ok=false
    fi

    write_step "Checking UV..."
    if command_exists uv; then
        write_ok "UV: $(uv --version 2>&1 | head -1)"
    else
        write_err "UV NOT found in PATH"
        all_ok=false
    fi

    write_step "Testing MCP server import..."
    if (cd "$PROJECT_ROOT" && uv run python -c "from src.server import mcp; print('MCP server OK')" 2>&1 | grep -q "MCP server OK"); then
        write_ok "MCP server module loads correctly"
    else
        write_warn "MCP server import issue"
    fi

    echo ""
    if $all_ok; then
        write_ok "All required dependencies are installed and configured!"
    else
        write_err "Some dependencies are missing."
    fi
}

# ── Main ────────────────────────────────────────────────────────────────────

# Plugin mode: delegate to scripts/install-plugin.sh
if $PLUGIN || $BUILD_ONLY; then
    PLUGIN_SCRIPT="$PROJECT_ROOT/scripts/install-plugin.sh"
    if [ ! -f "$PLUGIN_SCRIPT" ]; then
        write_err "scripts/install-plugin.sh not found"
        exit 1
    fi
    PLUGIN_ARGS=()
    $BUILD_ONLY && PLUGIN_ARGS+=("--build-only")
    $FORCE && PLUGIN_ARGS+=("--force")
    exec bash "$PLUGIN_SCRIPT" "${PLUGIN_ARGS[@]}"
fi

write_header "mcp-libre Linux Setup"

# Check if we have sudo for installs
if ! $CHECK_ONLY && [ "$(id -u)" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    write_warn "Not running as root. You may be prompted for sudo password."
    echo ""
fi

PYTHON_CMD=""

# Required dependencies
ensure_python || true
ensure_libreoffice || true
ensure_uv || true

# Optional dependencies
if ! $SKIP_OPTIONAL; then
    ensure_nodejs
    ensure_java
fi

if $CHECK_ONLY; then
    write_header "Check Complete"
    verify_setup
    exit 0
fi

# Project setup (only if all required deps are OK)
if [ -n "$PYTHON_CMD" ] && command_exists soffice && command_exists uv; then
    initialize_project
    setup_claude_config
else
    write_err "Cannot proceed with project setup: missing required dependencies."
    write_info "Fix the issues above and re-run this script."
    exit 1
fi

# Final verification
verify_setup

# Summary
write_header "Setup Complete!"
echo "  Next steps:"
echo "  1. Restart your terminal (to pick up PATH changes)"
echo "  2. Restart Claude Desktop (to load MCP server config)"
echo "  3. Test: uv run python src/main.py --test"
echo ""

if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "  Warnings:"
    for w in "${WARNINGS[@]}"; do
        echo "    - $w"
    done
    echo ""
fi

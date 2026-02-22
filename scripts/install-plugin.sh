#!/bin/bash
# Build and install the LibreOffice MCP plugin extension (.oxt).
#
# Usage:
#   ./install-plugin.sh                # Build + install (interactive)
#   ./install-plugin.sh --force        # Build + install (no prompts, kills LO)
#   ./install-plugin.sh --build-only   # Only create the .oxt
#   ./install-plugin.sh --uninstall    # Remove the extension
#   ./install-plugin.sh --uninstall --force

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$PROJECT_ROOT/plugin"
BUILD_DIR="$PROJECT_ROOT/build"
STAGING_DIR="$BUILD_DIR/staging"
OXT_FILE="$BUILD_DIR/libreoffice-mcp-extension.oxt"

EXTENSION_ID="org.mcp.libreoffice.extension"

# Parse args
FORCE=false
BUILD_ONLY=false
UNINSTALL=false
for arg in "$@"; do
    case "$arg" in
        --force)      FORCE=true ;;
        --build-only) BUILD_ONLY=true ;;
        --uninstall)  UNINSTALL=true ;;
        -h|--help)
            echo "Usage: $0 [--force] [--build-only] [--uninstall]"
            exit 0
            ;;
    esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────

confirm_or_force() {
    local prompt="$1"
    if $FORCE; then return 0; fi
    read -rp "$prompt (Y/n) " response
    [[ -z "$response" || "$response" =~ ^[Yy] ]]
}

# ── Find LibreOffice / unopkg ────────────────────────────────────────────────

find_unopkg() {
    for candidate in \
        /usr/bin/unopkg \
        /usr/lib/libreoffice/program/unopkg \
        /usr/lib64/libreoffice/program/unopkg \
        /opt/libreoffice*/program/unopkg \
        /snap/bin/libreoffice.unopkg; do
        for c in $candidate; do
            if [ -x "$c" ]; then
                echo "$c"
                return
            fi
        done
    done
    command -v unopkg 2>/dev/null || true
}

is_lo_running() {
    pgrep -x "soffice.bin" >/dev/null 2>&1
}

stop_libreoffice() {
    echo "[*] Closing LibreOffice..."
    for attempt in 1 2 3; do
        pkill -f soffice 2>/dev/null || true
        sleep 2
        if ! is_lo_running; then
            echo "[OK] LibreOffice closed"
            return 0
        fi
        echo "    Attempt $attempt/3 - processes still running, retrying..."
        sleep 2
    done
    if is_lo_running; then
        echo "[X] Could not close LibreOffice after 3 attempts"
        return 1
    fi
    echo "[OK] LibreOffice closed"
}

ensure_lo_stopped() {
    if ! is_lo_running; then return 0; fi
    echo "[!!] LibreOffice is running. It must be closed for unopkg."
    if ! confirm_or_force "Close LibreOffice now?"; then
        echo "[X] Cannot proceed while LibreOffice is running."
        return 1
    fi
    stop_libreoffice
}

# ── Fix Python imports ───────────────────────────────────────────────────────

fix_python_imports() {
    local dir="$1"
    for pyfile in "$dir"/*.py; do
        [ -f "$pyfile" ] || continue
        local original
        original=$(cat "$pyfile")
        local content
        # Fix relative imports
        content=$(echo "$original" | sed 's/from \.\([a-zA-Z_][a-zA-Z0-9_]*\) import/from \1 import/g')
        content=$(echo "$content" | sed 's/import \.\([a-zA-Z_][a-zA-Z0-9_]*\)/import \1/g')
        # Remove BOM
        content=$(echo "$content" | sed '1s/^\xEF\xBB\xBF//')
        printf '%s\n' "$content" > "$pyfile"
        if [ "$content" != "$original" ]; then
            echo "    Fixed imports in $(basename "$pyfile")"
        fi
    done
}

# ── Build .oxt ───────────────────────────────────────────────────────────────

build_oxt() {
    echo ""
    echo "=== Building .oxt ==="
    echo ""

    # Validate source files exist
    local required_files=(
        "pythonpath/registration.py"
        "pythonpath/uno_bridge.py"
        "pythonpath/mcp_server.py"
        "pythonpath/ai_interface.py"
        "pythonpath/version.py"
        "Addons.xcu"
        "ProtocolHandler.xcu"
        "MCPServerConfig.xcs"
        "MCPServerConfig.xcu"
        "OptionsDialog.xcu"
        "dialogs/MCPSettings.xdl"
        "icons/stopped_16.png"
        "icons/running_16.png"
        "icons/starting_16.png"
    )

    local missing=()
    for f in "${required_files[@]}"; do
        if [ ! -f "$PLUGIN_DIR/$f" ]; then
            missing+=("$f")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "[X] Missing source files in plugin/:"
        for f in "${missing[@]}"; do echo "    - $f"; done
        return 1
    fi

    # Clean previous build
    rm -rf "$STAGING_DIR"
    rm -f "$OXT_FILE"
    mkdir -p "$STAGING_DIR"

    # pythonpath/ -- helper modules
    echo "[*] Copying plugin files to staging..."
    mkdir -p "$STAGING_DIR/pythonpath"
    for f in uno_bridge.py mcp_server.py ai_interface.py version.py; do
        cp "$PLUGIN_DIR/pythonpath/$f" "$STAGING_DIR/pythonpath/"
    done

    # registration.py -> extension root
    cp "$PLUGIN_DIR/pythonpath/registration.py" "$STAGING_DIR/"

    # Fix relative imports
    echo "[*] Fixing Python imports for LibreOffice extension structure..."
    fix_python_imports "$STAGING_DIR/pythonpath"
    fix_python_imports "$STAGING_DIR"

    # META-INF/manifest.xml
    mkdir -p "$STAGING_DIR/META-INF"
    cat > "$STAGING_DIR/META-INF/manifest.xml" << 'MANIFEST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE manifest:manifest PUBLIC "-//OpenOffice.org//DTD Manifest 1.0//EN" "Manifest.dtd">
<manifest:manifest xmlns:manifest="http://openoffice.org/2001/manifest">
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.uno-component;type=Python" manifest:full-path="registration.py"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-schema" manifest:full-path="MCPServerConfig.xcs"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="MCPServerConfig.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="Addons.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="ProtocolHandler.xcu"/>
    <manifest:file-entry manifest:media-type="application/vnd.sun.star.configuration-data" manifest:full-path="OptionsDialog.xcu"/>
</manifest:manifest>
MANIFEST_EOF
    echo "    manifest.xml generated"

    # description.xml
    cat > "$STAGING_DIR/description.xml" << 'DESC_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/description/2006"
             xmlns:xlink="http://www.w3.org/1999/xlink">
    <identifier value="org.mcp.libreoffice.extension"/>
    <version value="1.1.0"/>
    <display-name>
        <name lang="en">LibreOffice MCP Server Extension</name>
    </display-name>
    <publisher>
        <name lang="en" xlink:href="https://github.com">MCP LibreOffice Team</name>
    </publisher>
</description>
DESC_EOF
    echo "    description.xml generated"

    # XCU/XCS config files
    for f in Addons.xcu ProtocolHandler.xcu MCPServerConfig.xcs MCPServerConfig.xcu OptionsDialog.xcu; do
        cp "$PLUGIN_DIR/$f" "$STAGING_DIR/"
    done

    # Dialogs
    mkdir -p "$STAGING_DIR/dialogs"
    cp "$PLUGIN_DIR/dialogs/MCPSettings.xdl" "$STAGING_DIR/dialogs/"

    # Icons
    mkdir -p "$STAGING_DIR/icons"
    cp "$PLUGIN_DIR/icons/"*.png "$STAGING_DIR/icons/"
    echo "    Copied $(ls "$STAGING_DIR/icons/"*.png 2>/dev/null | wc -l) icon files"

    # Text files
    for f in description-en.txt release-notes-en.txt; do
        [ -f "$PLUGIN_DIR/$f" ] && cp "$PLUGIN_DIR/$f" "$STAGING_DIR/"
    done

    # LICENSE from project root
    [ -f "$PROJECT_ROOT/LICENSE" ] && cp "$PROJECT_ROOT/LICENSE" "$STAGING_DIR/" && echo "    Included LICENSE"

    # Create .oxt (ZIP)
    echo "[*] Creating .oxt package..."
    mkdir -p "$BUILD_DIR"
    (cd "$STAGING_DIR" && zip -r -q "$OXT_FILE" .)

    if [ -f "$OXT_FILE" ]; then
        local size
        size=$(stat -c%s "$OXT_FILE" 2>/dev/null || stat -f%z "$OXT_FILE" 2>/dev/null)
        echo "[OK] Built: $OXT_FILE ($size bytes)"
    else
        echo "[X] Failed to create .oxt file"
        return 1
    fi

    # Clean staging
    rm -rf "$STAGING_DIR"
}

# ── Install / Uninstall ─────────────────────────────────────────────────────

install_extension() {
    local unopkg="$1"

    echo ""
    echo "=== Installing Extension ==="
    echo ""

    ensure_lo_stopped || return 1

    # Remove previous version
    echo "[*] Removing previous version (if any)..."
    if $unopkg remove "$EXTENSION_ID" 2>&1 | grep -qiE "not deployed|no such|aucune"; then
        echo "    No previous version found (OK)"
    else
        echo "    Previous version removed"
    fi
    sleep 2

    # Install new version
    echo "[*] Installing $OXT_FILE ..."
    if ! $unopkg add "$OXT_FILE" 2>&1; then
        echo "[X] unopkg add failed"
        echo "    Troubleshooting:"
        echo "    1. Make sure LibreOffice is fully closed"
        echo "    2. Try: $0 --uninstall --force"
        echo "    3. Then: $0 --force"
        return 1
    fi

    echo "[OK] Extension installed successfully!"

    # Verify
    sleep 2
    echo "[*] Verifying installation..."
    if $unopkg list 2>&1 | grep -q "$EXTENSION_ID"; then
        echo "[OK] Extension verified: $EXTENSION_ID is registered"
    else
        echo "[!!] Could not verify via unopkg list (often OK, LO will load it on start)"
    fi
}

uninstall_extension() {
    local unopkg="$1"

    echo ""
    echo "=== Uninstalling Extension ==="
    echo ""

    ensure_lo_stopped || return 1

    echo "[*] Removing extension $EXTENSION_ID ..."
    if $unopkg remove "$EXTENSION_ID" 2>&1 | grep -qiE "not deployed|no such|aucune"; then
        echo "    Extension was not installed"
    else
        echo "[OK] Extension removed"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

echo ""
echo "========================================"
echo "  LibreOffice MCP Plugin Installer"
echo "========================================"
echo ""

# Find unopkg
UNOPKG=$(find_unopkg)
if [ -z "$UNOPKG" ]; then
    echo "[X] unopkg not found. Install LibreOffice first."
    exit 1
fi
echo "[OK] unopkg: $UNOPKG"

# Uninstall mode
if $UNINSTALL; then
    uninstall_extension "$UNOPKG"
    exit $?
fi

# Build
build_oxt || exit 1

if $BUILD_ONLY; then
    echo ""
    echo "[OK] Build complete. Install manually with:"
    echo "    $UNOPKG add $OXT_FILE"
    exit 0
fi

# Install
install_extension "$UNOPKG" || exit 1

# Restart LibreOffice?
if confirm_or_force "Start LibreOffice now?"; then
    echo "[*] Starting LibreOffice..."
    soffice &
    echo "[OK] LibreOffice started"
    echo "    Check menu bar for 'MCP Server' entry"
fi

echo ""
echo "========================================"
echo "  Done!"
echo "========================================"
echo ""
echo "  Next steps:"
echo "  1. Open a document in LibreOffice"
echo "  2. MCP Server > Start MCP Server  (in the menu bar)"
echo "  3. Test: curl http://localhost:8765/health"
echo ""

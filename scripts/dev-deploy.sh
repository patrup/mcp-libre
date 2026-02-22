#!/bin/bash
# Dev-mode deploy: sync plugin/ to build/dev/ (fixing imports) and create
# a symlink in LO share/extensions/ so changes take effect on LO restart.
# No unopkg needed. Run with sudo the first time (for the symlink).
#
# Usage:
#   ./dev-deploy.sh          # Sync files + create symlink if missing
#   ./dev-deploy.sh --remove  # Remove the symlink

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$PROJECT_ROOT/plugin"
DEV_DIR="$PROJECT_ROOT/build/dev"
EXT_NAME="mcp-libre"

# ── Find LO extensions dir ──────────────────────────────────────────────────

LO_EXT_DIR=""
for p in \
    /usr/lib/libreoffice/share/extensions \
    /usr/lib64/libreoffice/share/extensions \
    /opt/libreoffice*/share/extensions \
    /snap/libreoffice/current/lib/libreoffice/share/extensions \
    /usr/local/lib/libreoffice/share/extensions; do
    # Handle glob
    for d in $p; do
        if [ -d "$d" ]; then
            LO_EXT_DIR="$d"
            break 2
        fi
    done
done

if [ -z "$LO_EXT_DIR" ]; then
    echo "[X] LibreOffice share/extensions not found"
    exit 1
fi

SYMLINK_PATH="$LO_EXT_DIR/$EXT_NAME"

# ── Remove mode ──────────────────────────────────────────────────────────────

if [ "${1:-}" = "--remove" ]; then
    if [ -L "$SYMLINK_PATH" ]; then
        sudo rm "$SYMLINK_PATH"
        echo "[OK] Symlink removed: $SYMLINK_PATH"
    else
        echo "[OK] No symlink to remove"
    fi
    exit 0
fi

# ── Helper: write file without BOM ──────────────────────────────────────────

write_no_bom() {
    # Remove BOM if present and write
    local file="$1"
    local content
    content=$(sed '1s/^\xEF\xBB\xBF//' "$file")
    printf '%s' "$content" > "$file"
}

# ── Sync plugin/ -> build/dev/ (with import fixes) ──────────────────────────

echo ""
echo "=== Dev Deploy ==="
echo ""

# Clean and recreate dev dir
rm -rf "$DEV_DIR"
mkdir -p "$DEV_DIR"

# registration.py -> root (UNO component entry point)
cp "$PLUGIN_DIR/pythonpath/registration.py" "$DEV_DIR/"

# pythonpath/ -- helper modules
mkdir -p "$DEV_DIR/pythonpath"
for f in uno_bridge.py mcp_server.py ai_interface.py main_thread_executor.py version.py; do
    cp "$PLUGIN_DIR/pythonpath/$f" "$DEV_DIR/pythonpath/"
done

# Fix relative imports in all .py files
fix_imports() {
    local dir="$1"
    for pyfile in "$dir"/*.py; do
        [ -f "$pyfile" ] || continue
        local original
        original=$(cat "$pyfile")
        local content
        content=$(echo "$original" | sed 's/from \.\([a-zA-Z_][a-zA-Z0-9_]*\) import/from \1 import/g')
        content=$(echo "$content" | sed 's/import \.\([a-zA-Z_][a-zA-Z0-9_]*\)/import \1/g')
        # Remove BOM
        content=$(echo "$content" | sed '1s/^\xEF\xBB\xBF//')
        printf '%s\n' "$content" > "$pyfile"
        if [ "$content" != "$original" ]; then
            echo "    Fixed imports: $(basename "$pyfile")"
        fi
    done
}
fix_imports "$DEV_DIR"
fix_imports "$DEV_DIR/pythonpath"

# AGENT.md (served by HTTP endpoint)
cp "$PROJECT_ROOT/AGENT.md" "$DEV_DIR/"

# XCU/XCS config files
for f in Addons.xcu ProtocolHandler.xcu MCPServerConfig.xcs MCPServerConfig.xcu OptionsDialog.xcu Jobs.xcu; do
    cp "$PLUGIN_DIR/$f" "$DEV_DIR/"
done

# Dialogs
mkdir -p "$DEV_DIR/dialogs"
cp "$PLUGIN_DIR/dialogs/MCPSettings.xdl" "$DEV_DIR/dialogs/"

# Icons
mkdir -p "$DEV_DIR/icons"
cp "$PLUGIN_DIR/icons/"*.png "$DEV_DIR/icons/"

# META-INF/manifest.xml
mkdir -p "$DEV_DIR/META-INF"
cat > "$DEV_DIR/META-INF/manifest.xml" << 'MANIFEST_EOF'
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
MANIFEST_EOF

# description.xml - read version from version.py
VERSION=$(grep -oP 'EXTENSION_VERSION\s*=\s*"\K[^"]+' "$PLUGIN_DIR/pythonpath/version.py" || echo "0.0.0")

cat > "$DEV_DIR/description.xml" << DESC_EOF
<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/description/2006"
             xmlns:xlink="http://www.w3.org/1999/xlink">
    <identifier value="org.mcp.libreoffice.extension"/>
    <version value="$VERSION"/>
    <display-name>
        <name lang="en">LibreOffice MCP Server Extension</name>
    </display-name>
    <publisher>
        <name lang="en" xlink:href="https://github.com">MCP LibreOffice Team</name>
    </publisher>
</description>
DESC_EOF

FILE_COUNT=$(find "$DEV_DIR" -type f | wc -l)
echo "[OK] Synced $FILE_COUNT files to build/dev/ (v$VERSION)"

# ── Create symlink if missing ────────────────────────────────────────────────

if [ -L "$SYMLINK_PATH" ] || [ -d "$SYMLINK_PATH" ]; then
    echo "[OK] Symlink exists: $SYMLINK_PATH"
else
    echo "[*] Creating symlink: $SYMLINK_PATH -> $DEV_DIR"
    sudo ln -s "$DEV_DIR" "$SYMLINK_PATH"
    echo "[OK] Symlink created"
fi

# ── Delete __pycache__ to avoid stale bytecode ──────────────────────────────

find "$DEV_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── Re-register bundled extensions (needed for Jobs.xcu / new components) ───

UNOPKG=""
for candidate in \
    /usr/bin/unopkg \
    /usr/lib/libreoffice/program/unopkg \
    /opt/libreoffice*/program/unopkg; do
    for c in $candidate; do
        if [ -x "$c" ]; then
            UNOPKG="$c"
            break 2
        fi
    done
done

if [ -n "$UNOPKG" ]; then
    # unopkg creates a user profile lock -- make sure no LO is running
    pkill -f soffice 2>/dev/null || true
    sleep 1
    $UNOPKG reinstall --bundled 2>/dev/null || true
    # Clean up residual lock
    LOCK_FILE="$HOME/.config/libreoffice/4/user/.lock"
    [ -f "$LOCK_FILE" ] && rm -f "$LOCK_FILE"
    echo "[OK] Bundled extensions re-registered (unopkg reinstall)"
else
    echo "[!] unopkg not found, skip bundled reinstall"
fi

echo ""
echo "=== Done ==="
echo "  Restart LibreOffice to load v$VERSION"
echo "  Edit plugin/*.py, run ./scripts/dev-deploy.sh, restart LO"
echo ""

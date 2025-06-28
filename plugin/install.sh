#!/bin/bash

# LibreOffice MCP Extension Installation Guide
# This script provides step-by-step installation and usage instructions

set -e

PLUGIN_DIR="/home/patrick/work/mcp/mcp-libre/plugin"
BUILD_DIR="/home/patrick/work/mcp/mcp-libre/build"

echo "🎯 LibreOffice MCP Extension - Installation & Usage Guide"
echo "========================================================"
echo ""

show_help() {
    cat << EOF
USAGE: $0 [COMMAND]

COMMANDS:
    install     - Build and install the extension
    uninstall   - Remove the extension from LibreOffice
    build       - Build the extension .oxt file only
    test        - Test the extension functionality
    status      - Check extension and server status
    help        - Show this help message

EXAMPLES:
    $0 install     # Build and install extension
    $0 test        # Test extension functionality
    $0 status      # Check if extension is working

EOF
}

check_requirements() {
    echo "🔍 Checking requirements..."
    
    # Check LibreOffice
    if ! command -v libreoffice >/dev/null 2>&1; then
        echo "❌ LibreOffice is not installed or not in PATH"
        echo "   Please install LibreOffice 7.0 or higher"
        exit 1
    else
        echo "✅ LibreOffice found: $(libreoffice --version | head -1)"
    fi
    
    # Check unopkg
    if ! command -v unopkg >/dev/null 2>&1; then
        echo "❌ unopkg command not found"
        echo "   Please ensure LibreOffice tools are properly installed"
        exit 1
    else
        echo "✅ unopkg found"
    fi
    
    # Check Python
    if ! command -v python3 >/dev/null 2>&1; then
        echo "❌ Python 3 is required for testing"
        echo "   Please install Python 3.7 or higher"
        exit 1
    else
        echo "✅ Python found: $(python3 --version)"
    fi
    
    # Check if requests is available for testing
    if ! python3 -c "import requests" >/dev/null 2>&1; then
        echo "⚠️  Python 'requests' module not found (needed for testing)"
        echo "   Install with: pip install requests"
    else
        echo "✅ Python requests module available"
    fi
    
    echo ""
}

build_extension() {
    echo "🏗️  Building extension..."
    cd "$PLUGIN_DIR"
    
    if [ ! -f "build.sh" ]; then
        echo "❌ Build script not found in $PLUGIN_DIR"
        exit 1
    fi
    
    ./build.sh
    echo ""
}

install_extension() {
    echo "📦 Installing extension..."
    
    # Build first
    build_extension
    
    # Check if extension file exists
    EXTENSION_FILE="$BUILD_DIR/libreoffice-mcp-extension.oxt"
    if [ ! -f "$EXTENSION_FILE" ]; then
        echo "❌ Extension file not found: $EXTENSION_FILE"
        exit 1
    fi
    
    # Remove existing installation
    echo "🗑️  Removing any existing installation..."
    unopkg remove org.mcp.libreoffice.extension 2>/dev/null || true
    
    # Install new version
    echo "⬇️  Installing extension..."
    unopkg add "$EXTENSION_FILE"
    
    echo "✅ Extension installed successfully!"
    echo ""
    echo "🔄 Please restart LibreOffice for the extension to take effect"
    echo ""
    echo "📋 After restart, you can:"
    echo "   1. Check Tools > MCP Server menu in LibreOffice"
    echo "   2. Run '$0 test' to verify functionality"
    echo "   3. Use http://localhost:8765 for AI assistant integration"
    echo ""
}

uninstall_extension() {
    echo "🗑️  Uninstalling extension..."
    
    if unopkg remove org.mcp.libreoffice.extension 2>/dev/null; then
        echo "✅ Extension uninstalled successfully!"
        echo "🔄 Please restart LibreOffice"
    else
        echo "⚠️  Extension was not installed or already removed"
    fi
    echo ""
}

test_extension() {
    echo "🧪 Testing extension functionality..."
    
    # Check if LibreOffice is running
    if ! pgrep -f "soffice" >/dev/null 2>&1; then
        echo "❌ LibreOffice is not running"
        echo "   Please start LibreOffice and try again"
        echo "   The extension needs LibreOffice to be running"
        exit 1
    fi
    
    # Check if test client is available
    if [ ! -f "$PLUGIN_DIR/test_plugin.py" ]; then
        echo "❌ Test client not found"
        exit 1
    fi
    
    # Run test
    echo "🚀 Running test client..."
    cd "$PLUGIN_DIR"
    python3 test_plugin.py
    echo ""
}

check_status() {
    echo "📊 Checking extension status..."
    
    # Check if extension is installed
    echo "🔍 Checking extension installation..."
    if unopkg list | grep -q "org.mcp.libreoffice.extension"; then
        echo "✅ Extension is installed"
    else
        echo "❌ Extension is not installed"
        echo "   Run '$0 install' to install it"
        return 1
    fi
    
    # Check if LibreOffice is running
    echo "🔍 Checking LibreOffice process..."
    if pgrep -f "soffice" >/dev/null 2>&1; then
        echo "✅ LibreOffice is running"
    else
        echo "⚠️  LibreOffice is not running"
        echo "   Start LibreOffice for the extension to work"
    fi
    
    # Check if MCP server is accessible
    echo "🔍 Checking MCP server..."
    if command -v curl >/dev/null 2>&1; then
        if curl -s http://localhost:8765/health >/dev/null 2>&1; then
            echo "✅ MCP server is accessible at http://localhost:8765"
            
            # Get server info
            SERVER_INFO=$(curl -s http://localhost:8765/ 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo "📋 Server info:"
                echo "$SERVER_INFO" | python3 -m json.tool 2>/dev/null || echo "$SERVER_INFO"
            fi
        else
            echo "❌ MCP server is not accessible"
            echo "   Check if LibreOffice is running with the extension"
        fi
    else
        echo "⚠️  curl not available, cannot test MCP server"
    fi
    
    echo ""
}

interactive_test() {
    echo "🎮 Starting interactive test mode..."
    
    if [ ! -f "$PLUGIN_DIR/test_plugin.py" ]; then
        echo "❌ Test client not found"
        exit 1
    fi
    
    cd "$PLUGIN_DIR"
    python3 test_plugin.py interactive
}

# Parse command line arguments
case "${1:-help}" in
    "install")
        check_requirements
        install_extension
        ;;
    "uninstall")
        uninstall_extension
        ;;
    "build")
        check_requirements
        build_extension
        ;;
    "test")
        check_requirements
        test_extension
        ;;
    "status")
        check_status
        ;;
    "interactive")
        check_requirements
        interactive_test
        ;;
    "help"|*)
        show_help
        ;;
esac

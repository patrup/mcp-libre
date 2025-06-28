#!/bin/bash

# LibreOffice MCP Server - Quick Test Script
# This script provides easy access to testing and server functionality

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR" && pwd )"

echo "🎯 LibreOffice MCP Server - Quick Test"
echo "======================================"
echo "Project: $PROJECT_ROOT"
echo ""

show_help() {
    cat << EOF
USAGE: $0 [COMMAND]

COMMANDS:
    help         - Show this help message
    test         - Run functionality tests
    server       - Start MCP server (use Ctrl+C to stop)
    client       - Run interactive test client
    version      - Show version information
    status       - Check LibreOffice installation

EXAMPLES:
    $0 test      # Run functionality tests
    $0 server    # Start MCP server for Claude Desktop integration
    $0 client    # Interactive testing

EOF
}

run_tests() {
    echo "🧪 Running LibreOffice MCP Server Tests..."
    echo ""
    cd "$PROJECT_ROOT"
    python src/main.py --test
}

start_server() {
    echo "🚀 Starting LibreOffice MCP Server..."
    echo "   Press Ctrl+C to stop the server"
    echo ""
    cd "$PROJECT_ROOT"
    python src/main.py
}

run_client() {
    echo "🎮 Running Interactive Test Client..."
    echo ""
    cd "$PROJECT_ROOT/tests"
    python test_client.py
}

show_version() {
    cd "$PROJECT_ROOT"
    python src/main.py --version
}

check_status() {
    echo "📊 Checking LibreOffice Installation..."
    echo ""
    
    # Check LibreOffice
    if command -v libreoffice >/dev/null 2>&1; then
        echo "✅ LibreOffice found: $(libreoffice --version | head -1)"
    else
        echo "❌ LibreOffice not found in PATH"
        echo "   Please install LibreOffice 7.0 or higher"
        return 1
    fi
    
    # Check Python
    echo "✅ Python: $(python --version 2>&1 || python3 --version)"
    
    # Check project structure
    if [ -f "$PROJECT_ROOT/src/libremcp.py" ]; then
        echo "✅ LibreOffice MCP Server source found"
    else
        echo "❌ LibreOffice MCP Server source not found"
        return 1
    fi
    
    echo ""
    echo "🎯 Ready to use! Try:"
    echo "   $0 test    # Run tests"
    echo "   $0 server  # Start server"
}

# Parse command line arguments
case "${1:-help}" in
    "test")
        run_tests
        ;;
    "server")
        start_server
        ;;
    "client")
        run_client
        ;;
    "version")
        show_version
        ;;
    "status")
        check_status
        ;;
    "help"|*)
        show_help
        ;;
esac

#!/bin/bash

# LibreOffice MCP Server Helper Script
# This script helps with testing, deployment, and integration
#
# Configuration:
# - MCP_CONFIG_PATH: Override the default MCP config location
#   Default: $HOME/Documents/mcp/mcp.config.json
#   Usage: MCP_CONFIG_PATH=/custom/path/mcp.config.json ./mcp-helper.sh proxy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MCP_CONFIG_PATH="${MCP_CONFIG_PATH:-$HOME/Documents/mcp/mcp.config.json}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  LibreOffice MCP Server Helper${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_dependencies() {
    print_header
    echo "Checking system prerequisites..."
    echo ""
    
    local all_ok=true
    
    # Check LibreOffice (Required)
    echo "LibreOffice (Required - Version 24.2+):"
    if command -v libreoffice >/dev/null 2>&1; then
        local version=$(libreoffice --version 2>/dev/null | head -1)
        print_status "LibreOffice is installed: $version"
        
        # Test headless mode
        if libreoffice --headless --help >/dev/null 2>&1; then
            print_status "LibreOffice headless mode is working"
        else
            print_warning "LibreOffice headless mode may have issues"
        fi
    else
        print_error "LibreOffice not found. Please install LibreOffice 24.2+"
        echo "  Ubuntu/Debian: sudo apt install libreoffice"
        echo "  macOS: brew install --cask libreoffice"
        echo "  Windows: Download from https://www.libreoffice.org/download/"
        all_ok=false
    fi
    echo ""
    
    # Check Python (Required)
    echo "Python (Required - Version 3.12+):"
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1)
        print_status "Python is installed: $python_version"
        
        # Check if version is 3.12+
        local version_check=$(python3 -c "import sys; print('ok' if sys.version_info >= (3, 12) else 'old')" 2>/dev/null || echo "error")
        if [ "$version_check" = "ok" ]; then
            print_status "Python version meets requirements (3.12+)"
        elif [ "$version_check" = "old" ]; then
            print_error "Python version is too old. Need Python 3.12+"
            all_ok=false
        else
            print_warning "Could not verify Python version"
        fi
    else
        print_error "Python3 not found. Please install Python 3.12+"
        echo "  Ubuntu/Debian: sudo apt install python3.12"
        echo "  macOS: brew install python@3.12"
        echo "  Windows: Download from https://www.python.org/downloads/"
        all_ok=false
    fi
    echo ""
    
    # Check UV Package Manager (Required)
    echo "UV Package Manager (Required - Latest):"
    if command -v uv >/dev/null 2>&1; then
        local uv_version=$(uv --version 2>/dev/null | head -1)
        print_status "UV package manager is available: $uv_version"
    else
        print_error "UV package manager not found. Please install uv."
        echo "  Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  Or: pip install uv"
        all_ok=false
    fi
    echo ""
    
    # Check Node.js/NPX (Optional - for Super Assistant proxy)
    echo "Node.js/NPX (Optional - for Super Assistant Chrome extension):"
    if command -v npx >/dev/null 2>&1; then
        local node_version=$(node --version 2>/dev/null)
        print_status "Node.js/NPX is available: $node_version"
        print_status "Super Assistant proxy support enabled"
    else
        print_warning "Node.js/NPX not found. Needed for Super Assistant Chrome extension."
        echo "  Ubuntu/Debian: sudo apt install nodejs npm"
        echo "  macOS: brew install node"
        echo "  Windows: Download from https://nodejs.org/"
    fi
    echo ""
    
    # Check Java (Optional - for advanced LibreOffice features)
    echo "Java (Optional - for advanced LibreOffice features like PDF generation):"
    if command -v java >/dev/null 2>&1; then
        local java_version=$(java -version 2>&1 | head -1)
        print_status "Java is installed: $java_version"
        print_status "Advanced LibreOffice features available"
    else
        print_warning "Java not found. Some LibreOffice features may be limited."
        echo "  Ubuntu/Debian: sudo apt install default-jre"
        echo "  macOS: brew install openjdk"
        echo "  Windows: Download from https://adoptium.net/"
    fi
    echo ""
    
    # Summary
    if [ "$all_ok" = true ]; then
        print_status "All required dependencies are satisfied!"
        echo "Ready to run LibreOffice MCP Server."
    else
        print_error "Some required dependencies are missing."
        echo "Please install the missing components and run '$0 check' again."
        exit 1
    fi
    
    echo ""
}

test_mcp_server() {
    echo "Testing MCP server functionality..."
    cd "$PROJECT_ROOT"
    
    # Run the built-in test
    if uv run python src/main.py --test; then
        print_status "MCP server test passed"
    else
        print_error "MCP server test failed"
        exit 1
    fi
    
    echo ""
}

start_proxy() {
    echo "Starting MCP proxy for Super Assistant..."
    
    if [ ! -f "$MCP_CONFIG_PATH" ]; then
        print_error "MCP configuration file not found: $MCP_CONFIG_PATH"
        exit 1
    fi
    
    print_status "Starting proxy with configuration: $MCP_CONFIG_PATH"
    print_warning "Press Ctrl+C to stop the proxy"
    echo ""
    
    npx @srbhptl39/mcp-superassistant-proxy@latest --config "$MCP_CONFIG_PATH"
}

run_demo() {
    echo "Running interactive demo..."
    cd "$PROJECT_ROOT"
    
    uv run python tests/test_client.py
}

show_requirements() {
    print_header
    echo "LibreOffice MCP Server - System Requirements"
    echo ""
    
    echo -e "${BLUE}Required Components:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    echo "1. LibreOffice (Version 24.2 or higher)"
    echo "   Purpose: Document processing engine"
    echo "   Features: Create, read, convert documents"
    echo "   Install:"
    echo "     • Ubuntu/Debian: sudo apt install libreoffice"
    echo "     • CentOS/RHEL: sudo yum install libreoffice"
    echo "     • macOS: brew install --cask libreoffice"
    echo "     • Windows: https://www.libreoffice.org/download/"
    echo ""
    
    echo "2. Python (Version 3.12 or higher)"
    echo "   Purpose: Runtime environment for MCP server"
    echo "   Features: FastMCP framework, async operations"
    echo "   Install:"
    echo "     • Ubuntu/Debian: sudo apt install python3.12 python3.12-venv"
    echo "     • macOS: brew install python@3.12"
    echo "     • Windows: https://www.python.org/downloads/"
    echo ""
    
    echo "3. UV Package Manager (Latest version)"
    echo "   Purpose: Fast Python package management"
    echo "   Features: Dependency resolution, virtual environments"
    echo "   Install:"
    echo "     • All platforms: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "     • Alternative: pip install uv"
    echo ""
    
    echo -e "${YELLOW}Optional Components:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    echo "4. Node.js & NPM (Version 18+)"
    echo "   Purpose: Super Assistant Chrome extension proxy"
    echo "   Features: Browser integration, real-time document processing"
    echo "   Install:"
    echo "     • Ubuntu/Debian: sudo apt install nodejs npm"
    echo "     • macOS: brew install node"
    echo "     • Windows: https://nodejs.org/"
    echo ""
    
    echo "5. Java Runtime Environment (JRE 11+)"
    echo "   Purpose: Advanced LibreOffice features"
    echo "   Features: PDF generation, complex document processing"
    echo "   Install:"
    echo "     • Ubuntu/Debian: sudo apt install default-jre"
    echo "     • macOS: brew install openjdk"
    echo "     • Windows: https://adoptium.net/"
    echo ""
    
    echo -e "${BLUE}Integration Targets:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    echo "• Claude Desktop (Anthropic)"
    echo "  - Direct MCP protocol integration"
    echo "  - Configuration via claude_desktop_config.json"
    echo ""
    
    echo "• Super Assistant Chrome Extension"
    echo "  - Browser-based document processing"
    echo "  - Requires MCP proxy server (Node.js)"
    echo ""
    
    echo "• Direct MCP Clients"
    echo "  - Python applications using FastMCP"
    echo "  - Custom integrations via stdio transport"
    echo ""
    
    echo -e "${GREEN}Minimum System Requirements:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• Operating System: Linux, macOS, Windows"
    echo "• Memory: 2GB RAM (4GB recommended)"
    echo "• Storage: 2GB free space for LibreOffice + documents"
    echo "• Network: Internet access for initial setup only"
    echo ""
    
    echo "Run '$0 check' to verify your system meets these requirements."
    echo ""
}

show_info() {
    print_header
    echo "LibreOffice MCP Server - Project Information"
    echo ""
    
    echo -e "${BLUE}Project Details:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• Name: LibreOffice MCP Server (mcp-libre)"
    echo "• Version: 0.1.0"
    echo "• License: MIT License"
    echo "• Purpose: Model Context Protocol server for LibreOffice document processing"
    echo ""
    
    echo -e "${GREEN}Key Features:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• Document Creation & Editing (Writer, Calc, Impress, Draw)"
    echo "• Format Conversion (50+ formats including PDF, DOCX, HTML)"
    echo "• Content Extraction & Analysis"
    echo "• Batch Operations & Document Search"
    echo "• AI Assistant Integration (Claude Desktop, Super Assistant)"
    echo ""
    
    echo -e "${YELLOW}License Information:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• License Type: MIT License (Permissive)"
    echo "• Commercial Use: ✅ Allowed"
    echo "• Modification: ✅ Allowed"
    echo "• Distribution: ✅ Allowed"
    echo "• Private Use: ✅ Allowed"
    echo ""
    echo "For full license text, see: LICENSE"
    echo "For other license options, see: LICENSE_OPTIONS.md"
    echo ""
    
    echo -e "${BLUE}File Structure:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• libremcp.py - Main MCP server implementation"
    echo "• main.py - Entry point script"
    echo "• test_client.py - Test client for validation"
    echo "• mcp-helper.sh - Management and testing helper"
    echo "• pyproject.toml - Project configuration"
    echo "• Documentation: README.md, EXAMPLES.md, etc."
    echo ""
}

show_config() {
    echo "Current MCP configuration:"
    echo "Config file: $MCP_CONFIG_PATH"
    echo ""
    if [ -f "$MCP_CONFIG_PATH" ]; then
        cat "$MCP_CONFIG_PATH"
    else
        print_error "Configuration file not found"
    fi
    echo ""
}

show_help() {
    print_header
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  requirements Show detailed system requirements and installation guides"
    echo "  check        Check dependencies and system requirements"
    echo "  test         Run MCP server functionality tests"
    echo "  demo         Run interactive demo of MCP capabilities"
    echo "  proxy        Start the MCP proxy for Super Assistant"
    echo "  config       Show current MCP configuration"
    echo "  info         Show project information and license details"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 requirements             # Show detailed system requirements"
    echo "  $0 check                    # Check if everything is set up correctly"
    echo "  $0 test                     # Test the LibreOffice MCP server"
    echo "  $0 proxy                    # Start proxy for Super Assistant"
    echo "  $0 demo                     # See what the server can do"
    echo ""
    echo "Integration Workflow:"
    echo "  1. Run '$0 requirements' to see what you need"
    echo "  2. Install required components"
    echo "  3. Run '$0 check' to verify setup"
    echo "  4. Run '$0 test' to test functionality"
    echo "  5. Run './generate-config.sh' to create configurations"
    echo "     - For Claude Desktop: './generate-config.sh claude'"
    echo "     - For Super Assistant: './generate-config.sh mcp'"
    echo "     - For both: './generate-config.sh both'"
    echo "  6. Run '$0 proxy' to start proxy (Super Assistant only)"
    echo "  7. Configure AI assistant to use the MCP server"
    echo ""
}

# Main command handling
case "${1:-help}" in
    "requirements"|"req")
        show_requirements
        ;;
    "check")
        check_dependencies
        ;;
    "test")
        check_dependencies
        test_mcp_server
        ;;
    "demo")
        check_dependencies
        run_demo
        ;;
    "proxy")
        check_dependencies
        start_proxy
        ;;
    "config")
        show_config
        ;;
    "info"|"information")
        show_info
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

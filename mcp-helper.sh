#!/bin/bash

# LibreOffice MCP Server Helper Script
# This script helps with testing, deployment, and integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_CONFIG_PATH="/home/patrick/Documents/mcp/mcp.config.json"

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
    echo "Checking dependencies..."
    
    # Check LibreOffice
    if command -v libreoffice >/dev/null 2>&1; then
        print_status "LibreOffice is installed"
        libreoffice --version
    else
        print_error "LibreOffice not found. Please install LibreOffice."
        exit 1
    fi
    
    # Check Python and uv
    if command -v uv >/dev/null 2>&1; then
        print_status "UV package manager is available"
    else
        print_error "UV package manager not found. Please install uv."
        exit 1
    fi
    
    # Check Node.js for proxy
    if command -v npx >/dev/null 2>&1; then
        print_status "Node.js/NPX is available"
        node --version
    else
        print_warning "Node.js/NPX not found. Needed for MCP proxy."
    fi
    
    echo ""
}

test_mcp_server() {
    echo "Testing MCP server functionality..."
    cd "$SCRIPT_DIR"
    
    # Run the built-in test
    if uv run python libremcp.py --test; then
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
    cd "$SCRIPT_DIR"
    
    uv run python test_client.py
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
    echo "  check       Check dependencies and system requirements"
    echo "  test        Run MCP server functionality tests"
    echo "  demo        Run interactive demo of MCP capabilities"
    echo "  proxy       Start the MCP proxy for Super Assistant"
    echo "  config      Show current MCP configuration"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check                    # Check if everything is set up correctly"
    echo "  $0 test                     # Test the LibreOffice MCP server"
    echo "  $0 proxy                    # Start proxy for Super Assistant"
    echo "  $0 demo                     # See what the server can do"
    echo ""
    echo "Integration:"
    echo "  1. Run '$0 check' to verify setup"
    echo "  2. Run '$0 test' to test functionality"
    echo "  3. Run '$0 proxy' to start the proxy server"
    echo "  4. Configure Super Assistant extension to use http://localhost:3000"
    echo ""
}

# Main command handling
case "${1:-help}" in
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

#!/bin/bash

# Generate MCP Configuration Script
# Creates personalized configuration files from templates for both
# Claude Desktop and Super Assistant integrations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_TEMPLATE="$SCRIPT_DIR/mcp.config.json.template"
CLAUDE_TEMPLATE="$SCRIPT_DIR/claude_config.json.template"

# Default output locations
DEFAULT_MCP_DIR="$HOME/Documents/mcp"
DEFAULT_CLAUDE_CONFIG="$HOME/.config/claude/claude_desktop_config.json"

# Parse command line arguments
TARGET_TYPE="${1:-both}"  # both, claude, or mcp
CUSTOM_DIR="${2:-}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${BLUE}🔧 LibreOffice MCP Configuration Generator${NC}"
    echo ""
    echo "Usage: $0 [TYPE] [CUSTOM_DIR]"
    echo ""
    echo "TYPE options:"
    echo "  both    - Generate both Claude Desktop and Super Assistant configs (default)"
    echo "  claude  - Generate only Claude Desktop config"
    echo "  mcp     - Generate only Super Assistant/MCP proxy config"
    echo ""
    echo "CUSTOM_DIR:"
    echo "  Override default output directory for MCP config"
    echo "  (Claude config always goes to ~/.config/claude/)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Generate both configs in default locations"
    echo "  $0 claude                   # Generate only Claude Desktop config"
    echo "  $0 mcp /custom/path         # Generate MCP config in custom directory"
    echo "  $0 both /custom/mcp/path    # Generate both, MCP in custom directory"
    echo ""
}

generate_claude_config() {
    local claude_dir="$(dirname "$DEFAULT_CLAUDE_CONFIG")"
    local claude_file="$DEFAULT_CLAUDE_CONFIG"
    
    echo -e "${BLUE}📋 Generating Claude Desktop configuration...${NC}"
    
    # Create Claude config directory if it doesn't exist
    if [ ! -d "$claude_dir" ]; then
        echo -e "${YELLOW}Creating directory: $claude_dir${NC}"
        mkdir -p "$claude_dir"
    fi
    
    # Check if Claude config already exists
    if [ -f "$claude_file" ]; then
        echo -e "${YELLOW}⚠ Claude Desktop config already exists: $claude_file${NC}"
        echo "Do you want to overwrite it? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Claude configuration generation skipped."
            return 0
        fi
    fi
    
    # Generate the Claude configuration file
    sed "s|/path/to/mcp-libre|$SCRIPT_DIR|g" "$CLAUDE_TEMPLATE" > "$claude_file"
    
    echo -e "${GREEN}✓ Claude Desktop config created: $claude_file${NC}"
    return 0
}

generate_mcp_config() {
    local output_dir="${CUSTOM_DIR:-$DEFAULT_MCP_DIR}"
    local output_file="$output_dir/mcp.config.json"
    
    echo -e "${BLUE}🔌 Generating Super Assistant MCP configuration...${NC}"
    
    # Create output directory if it doesn't exist
    if [ ! -d "$output_dir" ]; then
        echo -e "${YELLOW}Creating directory: $output_dir${NC}"
        mkdir -p "$output_dir"
    fi
    
    # Check if MCP config already exists
    if [ -f "$output_file" ]; then
        echo -e "${YELLOW}⚠ MCP configuration file already exists: $output_file${NC}"
        echo "Do you want to overwrite it? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "MCP configuration generation skipped."
            return 0
        fi
    fi
    
    # Generate the MCP configuration file
    sed "s|/path/to/mcp-libre|$SCRIPT_DIR|g" "$MCP_TEMPLATE" > "$output_file"
    
    echo -e "${GREEN}✓ MCP configuration created: $output_file${NC}"
    return 0
}

show_summary() {
    echo ""
    echo -e "${GREEN}🎉 Configuration Generation Complete!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [[ "$TARGET_TYPE" == "both" || "$TARGET_TYPE" == "claude" ]]; then
        echo -e "${BLUE}Claude Desktop Integration:${NC}"
        echo "1. Restart Claude Desktop application"
        echo "2. The LibreOffice MCP server will be available automatically"
        echo "3. Try: 'Create a new document and save it as report.odt'"
        echo ""
    fi
    
    if [[ "$TARGET_TYPE" == "both" || "$TARGET_TYPE" == "mcp" ]]; then
        echo -e "${BLUE}Super Assistant Integration:${NC}"
        echo "1. Start the proxy: ./mcp-helper.sh proxy"
        echo "2. Configure Super Assistant with: http://localhost:3006"
        echo "3. Try: 'Read the content from my document at ~/Documents/file.odt'"
        echo ""
    fi
    
    echo -e "${YELLOW}Need help?${NC} Run: ./mcp-helper.sh help"
}

# Main execution
case "$TARGET_TYPE" in
    "help"|"--help"|"-h")
        show_help
        exit 0
        ;;
    "claude")
        echo -e "${BLUE}🔧 LibreOffice MCP Configuration Generator${NC}"
        echo ""
        generate_claude_config
        show_summary
        ;;
    "mcp")
        echo -e "${BLUE}🔧 LibreOffice MCP Configuration Generator${NC}"
        echo ""
        generate_mcp_config
        show_summary
        ;;
    "both")
        echo -e "${BLUE}🔧 LibreOffice MCP Configuration Generator${NC}"
        echo ""
        generate_claude_config
        echo ""
        generate_mcp_config
        show_summary
        ;;
    *)
        echo -e "${RED}✗ Unknown configuration type: $TARGET_TYPE${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

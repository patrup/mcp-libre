#!/bin/bash

# Generate MCP Configuration Script
# Creates a personalized mcp.config.json file from the template

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/mcp.config.json.template"
OUTPUT_DIR="${1:-$HOME/Documents/mcp}"
OUTPUT_FILE="$OUTPUT_DIR/mcp.config.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 LibreOffice MCP Configuration Generator${NC}"
echo ""

# Create output directory if it doesn't exist
if [ ! -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}Creating directory: $OUTPUT_DIR${NC}"
    mkdir -p "$OUTPUT_DIR"
fi

# Check if config already exists
if [ -f "$OUTPUT_FILE" ]; then
    echo -e "${YELLOW}⚠ Configuration file already exists: $OUTPUT_FILE${NC}"
    echo "Do you want to overwrite it? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Configuration generation cancelled."
        exit 0
    fi
fi

# Generate the configuration file
echo -e "${BLUE}Generating configuration file...${NC}"
sed "s|/path/to/mcp-libre|$SCRIPT_DIR|g" "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo -e "${GREEN}✓ Configuration file created: $OUTPUT_FILE${NC}"
echo ""
echo "Configuration contents:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat "$OUTPUT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✓ Ready to use with Super Assistant!${NC}"
echo ""
echo "Next steps:"
echo "1. Start the proxy: ./mcp-helper.sh proxy"
echo "2. Configure Super Assistant to use: http://localhost:3006"
echo ""

#!/bin/bash

# LibreOffice MCP Extension Build Script
# This script packages the extension into an .oxt file for installation

set -e

PLUGIN_DIR="/home/patrick/work/mcp/mcp-libre/plugin"
BUILD_DIR="/home/patrick/work/mcp/mcp-libre/build"
EXTENSION_NAME="libreoffice-mcp-extension"
VERSION="1.0.0"

echo "🏗️  Building LibreOffice MCP Extension v${VERSION}"

# Create build directory
echo "📁 Creating build directory..."
mkdir -p "$BUILD_DIR"
cd "$PLUGIN_DIR"

# Clean previous builds
rm -f "$BUILD_DIR/${EXTENSION_NAME}-${VERSION}.oxt"
rm -f "$BUILD_DIR/${EXTENSION_NAME}.oxt"

echo "📦 Packaging extension files..."

# Create the .oxt file (which is just a ZIP archive)
zip -r "$BUILD_DIR/${EXTENSION_NAME}-${VERSION}.oxt" \
    META-INF/ \
    pythonpath/ \
    *.xml \
    *.txt \
    -x "*.pyc" "*/__pycache__/*"

# Create a symlink for easier access
ln -sf "${EXTENSION_NAME}-${VERSION}.oxt" "$BUILD_DIR/${EXTENSION_NAME}.oxt"

echo "✅ Extension built successfully!"
echo "📁 Output: $BUILD_DIR/${EXTENSION_NAME}-${VERSION}.oxt"
echo ""
echo "🚀 To install the extension:"
echo "   1. Open LibreOffice"
echo "   2. Go to Tools > Extension Manager"
echo "   3. Click 'Add' and select the .oxt file"
echo "   4. Restart LibreOffice"
echo ""
echo "🔧 Or install via command line:"
echo "   unopkg add \"$BUILD_DIR/${EXTENSION_NAME}-${VERSION}.oxt\""
echo ""
echo "🌐 After installation, the MCP server will be available at:"
echo "   http://localhost:8765"

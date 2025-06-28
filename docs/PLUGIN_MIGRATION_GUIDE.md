# 🔄 Migration Guide: External Server → LibreOffice Plugin

## 🎯 Overview

This guide helps you migrate from the external MCP server to the new LibreOffice plugin extension, which provides significantly better performance and capabilities.

## 📊 Benefits of Migration

| Feature | External Server | LibreOffice Plugin |
|---------|----------------|-------------------|
| **Performance** | ⭐⭐ (subprocess calls) | ⭐⭐⭐⭐⭐ (direct UNO API) |
| **Real-time Editing** | ⭐⭐ (file-based) | ⭐⭐⭐⭐⭐ (live objects) |
| **Startup Time** | ⭐⭐ (LibreOffice startup) | ⭐⭐⭐⭐⭐ (instant) |
| **Multi-document** | ⭐⭐ (file operations) | ⭐⭐⭐⭐⭐ (all open docs) |
| **GUI Integration** | ⭐ (none) | ⭐⭐⭐⭐⭐ (native menus) |
| **Advanced Features** | ⭐⭐⭐ (limited) | ⭐⭐⭐⭐⭐ (full access) |

## 🚀 Quick Migration (5 Minutes)

### Step 1: Install the Plugin
```bash
cd plugin/
./install.sh install
```

### Step 2: Update AI Assistant Configuration

**For Claude Desktop:**
```json
{
  "mcpServers": {
    "libreoffice-plugin": {
      "command": "curl",
      "args": [
        "-X", "POST", 
        "http://localhost:8765/execute",
        "-H", "Content-Type: application/json",
        "-d", "{\"tool\": \"TOOL_NAME\", \"parameters\": PARAMETERS}"
      ]
    }
  }
}
```

**For Super Assistant:**
Change the server URL from your external server to:
```
http://localhost:8765
```

### Step 3: Test the Migration
```bash
./install.sh test
```

### Step 4: Remove External Server (Optional)
Once you've verified the plugin works, you can stop using the external server.

## 🔧 Detailed Migration Steps

### 1. Backup Current Configuration

**Claude Desktop:**
```bash
cp ~/.config/claude/claude_desktop_config.json ~/.config/claude/claude_desktop_config.json.backup
```

**Super Assistant:**
```bash
cp ~/Documents/mcp/mcp.config.json ~/Documents/mcp/mcp.config.json.backup
```

### 2. Install LibreOffice Plugin

```bash
# Navigate to plugin directory
cd /home/patrick/work/mcp/mcp-libre/plugin

# Check prerequisites
./install.sh status

# Install the extension
./install.sh install

# Restart LibreOffice
pkill soffice || true
libreoffice &
```

### 3. Verify Plugin Installation

```bash
# Check extension status
./install.sh status

# Run comprehensive tests
./install.sh test

# Interactive testing (optional)
./install.sh interactive
```

### 4. Update AI Assistant Configurations

#### Claude Desktop Migration

Replace your existing LibreOffice MCP server configuration:

**Before (External Server):**
```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "python",
      "args": ["/path/to/mcp-libre/src/main.py"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-libre"
      }
    }
  }
}
```

**After (Plugin):**
```json
{
  "mcpServers": {
    "libreoffice-plugin": {
      "command": "curl",
      "args": [
        "-s", "-X", "POST",
        "http://localhost:8765/execute",
        "-H", "Content-Type: application/json",
        "-d", "{\"tool\": \"TOOL_NAME\", \"parameters\": PARAMETERS}"
      ]
    }
  }
}
```

#### Super Assistant Migration

**Before (External Server via Proxy):**
```bash
npx @srbhptl39/mcp-superassistant-proxy@latest --config ~/Documents/mcp/mcp.config.json
# Server URL: http://localhost:3006
```

**After (Direct Plugin):**
```
Server URL: http://localhost:8765
```
No proxy needed!

### 5. Test Migration Success

#### Basic Functionality Test
```bash
# Test server accessibility
curl http://localhost:8765/health

# List available tools
curl http://localhost:8765/tools

# Test document creation
curl -X POST http://localhost:8765/tools/create_document_live \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "writer"}'
```

#### AI Assistant Test

**Claude Desktop:**
- Ask: *"Create a new Writer document and add some text"*
- Verify the document appears in LibreOffice

**Super Assistant:**
- Use the command: *"Create a document with the title 'Migration Test'"*
- Check that it works without the proxy

## 🔄 Tool Name Mapping

Most tool names remain the same, but some have new "live" variants:

| External Server | LibreOffice Plugin | Notes |
|----------------|-------------------|-------|
| `create_document` | `create_document_live` | Creates in active LibreOffice instance |
| `read_document_text` | `get_text_content_live` | Reads from active document |
| `insert_text_at_position` | `insert_text_live` | Inserts in active document |
| `get_document_info` | `get_document_info_live` | Gets info from active document |
| *(new)* | `format_text_live` | Apply formatting to selected text |
| *(new)* | `list_open_documents` | List all open documents |
| `convert_document` | `export_document_live` | Export active document |

## 🎯 New Capabilities with Plugin

### Real-time Editing
```bash
# Create document
curl -X POST http://localhost:8765/tools/create_document_live \
  -H "Content-Type: application/json" \
  -d '{"doc_type": "writer"}'

# Insert text (see it appear immediately in LibreOffice)
curl -X POST http://localhost:8765/tools/insert_text_live \
  -H "Content-Type: application/json" \
  -d '{"text": "Live editing in action!"}'

# Format the text (select it first in LibreOffice)
curl -X POST http://localhost:8765/tools/format_text_live \
  -H "Content-Type: application/json" \
  -d '{"bold": true, "font_size": 16}'
```

### Multi-document Support
```bash
# List all open documents
curl http://localhost:8765/tools/list_open_documents

# Work with specific documents by switching focus in LibreOffice
```

### Advanced Document Operations
```bash
# Save current document
curl -X POST http://localhost:8765/tools/save_document_live \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/home/user/Documents/saved-doc.odt"}'

# Export to PDF
curl -X POST http://localhost:8765/tools/export_document_live \
  -H "Content-Type: application/json" \
  -d '{
    "export_format": "pdf",
    "file_path": "/home/user/Documents/exported.pdf"
  }'
```

## 🔧 Control and Management

### LibreOffice Menu Integration
After installation, access plugin controls via:
- **Tools > MCP Server > Start MCP Server**
- **Tools > MCP Server > Stop MCP Server**
- **Tools > MCP Server > Restart MCP Server**
- **Tools > MCP Server > Show Server Status**

### Command Line Management
```bash
# Check status
./install.sh status

# Restart if needed
./install.sh install

# Uninstall if necessary
./install.sh uninstall
```

## 🐛 Troubleshooting Migration

### Plugin Not Loading
```bash
# Check LibreOffice version
libreoffice --version  # Should be 7.0+

# Verify extension installation
unopkg list | grep mcp

# Check error logs
journalctl -f | grep soffice
```

### HTTP Server Not Starting
```bash
# Check if port 8765 is in use
netstat -tlnp | grep 8765

# Restart LibreOffice
pkill soffice
libreoffice &

# Check plugin status
./install.sh status
```

### AI Assistant Connection Issues
```bash
# Test server manually
curl http://localhost:8765/health

# Verify configuration syntax
cat ~/.config/claude/claude_desktop_config.json | python3 -m json.tool

# Test tool execution
curl -X POST http://localhost:8765/tools/get_document_info_live
```

## 🎉 Migration Complete!

Once migrated successfully, you'll have:

✅ **10x Performance Improvement** - Direct UNO API access  
✅ **Real-time Visual Feedback** - See changes instantly  
✅ **Native Integration** - LibreOffice menu controls  
✅ **Multi-document Support** - Work with all open documents  
✅ **Advanced Capabilities** - Full LibreOffice feature access  
✅ **Auto-start** - Available whenever LibreOffice runs  

Enjoy the enhanced LibreOffice MCP experience! 🚀

## 🔗 Resources

- **Plugin Documentation**: [`plugin/README.md`](../plugin/README.md)
- **Installation Guide**: [`plugin/install.sh help`](../plugin/install.sh)
- **Test Client**: [`plugin/test_plugin.py`](../plugin/test_plugin.py)
- **Original Design**: [`docs/LIBREOFFICE_PLUGIN_DESIGN.md`](LIBREOFFICE_PLUGIN_DESIGN.md)

# LibreOffice MCP Server

A comprehensive Model Context Protocol (MCP) server that provides tools and resources for interacting with LibreOffice documents. This server enables AI assistants and other MCP clients to create, read, convert, and manipulate LibreOffice documents programmatically.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LibreOffice](https://img.shields.io/badge/LibreOffice-24.2+-green.svg)](https://www.libreoffice.org/)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-2.x-orange.svg)](https://py.sdk.modelcontextprotocol.io/)

## 📂 Repository Structure

This repository is organized into logical directories:

- **`src/`** - Core MCP server implementation
- **`tests/`** - Test suite and validation scripts  
- **`examples/`** - Demo scripts and usage examples
- **`config/`** - Configuration templates for integrations
- **`scripts/`** - Utility scripts for setup and management
- **`docs/`** - Comprehensive documentation

For detailed information, see [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md).

## 🚀 Features

### Optional LibreOffice Extension
- **Native Integration**: Embedded MCP server directly in LibreOffice
- **Real-time Editing**: Live document manipulation with instant visual feedback
- **Multi-document**: Work with all open LibreOffice documents
- **HTTP API**: External AI assistant access via localhost:8765

### Document Operations
- **Create Documents**: New Writer, Calc, Impress, and Draw documents
- **Read Content**: Extract text from any LibreOffice document
- **Convert Formats**: Convert between 50+ formats (PDF, DOCX, HTML, etc.)
- **Edit Documents**: Insert, append, or replace text in Writer documents
- **Document Info**: Get detailed metadata about documents

### Spreadsheet Operations
- **Read Spreadsheets**: Extract data from Calc spreadsheets and Excel files
- **Structured Data**: Get data as 2D arrays with row/column information

### Advanced Tools
- **Document Search**: Find documents containing specific text
- **Batch Convert**: Convert multiple documents simultaneously
- **Merge Documents**: Combine multiple documents into one
- **Document Analysis**: Get detailed statistics (word count, sentences, etc.)

### Live Viewing & Real-time Editing
- **GUI Integration**: Open documents in LibreOffice for live viewing
- **Real-time Updates**: See changes as AI assistants modify documents
- **Change Monitoring**: Watch documents for modifications in real-time
- **Interactive Sessions**: Create live editing sessions with automatic refresh

### MCP Resources
- **Document Discovery**: List all LibreOffice documents (`documents://`)
- **Content Access**: Access specific document content (`document://{path}`)

## 📋 Requirements

- **LibreOffice**: 24.2+ (must be accessible via command line)
- **Python**: 3.12+
- **UV Package Manager**: For dependency management

For detailed installation instructions for all platforms, run:
```bash
./mcp-helper.sh requirements
```

## 🛠 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/patrup/mcp-libre/
   cd mcp-libre
   ```

2. **Check prerequisites**:
   ```bash
   ./mcp-helper.sh requirements  # Show detailed requirements
   ./mcp-helper.sh check         # Verify your system
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Make helper script executable**:
   ```bash
   chmod +x mcp-helper.sh
   ```

## 🎯 Quick Start

### Test the Server
```bash
# Run the automated suite
uv run pytest -q

# Exercise the actual stdio server process
uv run pytest -q tests/test_stdio_protocol.py

# Run the LibreOffice smoke test; artifacts remain in test-output/
uv run python src/main.py --test
```

### Start MCP Server
```bash
# MCP stdio mode
uv run python src/main.py

# Show help and options
uv run python src/main.py --help
```

### Integration with Super Assistant
```bash
# Start the MCP proxy
./mcp-helper.sh proxy

# Then configure Super Assistant extension:
# Server URL: http://localhost:3006
```

## 🔧 Available Tools

| Tool | Description |
|------|-------------|
| `create_document` | Create new LibreOffice documents |
| `read_document_text` | Extract text from documents |
| `convert_document` | Convert between formats |
| `get_document_info` | Get document metadata |
| `read_spreadsheet_data` | Read spreadsheet data |
| `insert_text_at_position` | Edit document text |
| `search_documents` | Search documents by content |
| `batch_convert_documents` | Batch format conversion |
| `merge_text_documents` | Merge multiple documents |
| `get_document_statistics` | Document analysis |
| `open_document_in_libreoffice` | Open document in GUI for live viewing |
| `create_live_editing_session` | Start live editing with real-time preview |
| `watch_document_changes` | Monitor document changes in real-time |
| `refresh_document_in_libreoffice` | Force document refresh in GUI |

## 📚 Documentation

- **[Prerequisites](docs/PREREQUISITES.md)**: Quick reference for system requirements
- **[Plugin Migration Guide](docs/PLUGIN_MIGRATION_GUIDE.md)**: Migrate from external server to plugin
- **[Examples](docs/EXAMPLES.md)**: Code examples and usage patterns
- **[Live Viewing Guide](docs/LIVE_VIEWING_GUIDE.md)**: See changes live in LibreOffice GUI
- **[Super Assistant Setup](docs/SUPER_ASSISTANT_SETUP.md)**: Chrome extension integration
- **[ChatGPT Browser Guide](docs/CHATGPT_BROWSER_GUIDE.md)**: Using with ChatGPT and alternatives
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[Quick Start](docs/QUICK_START.md)**: Quick reference guide
- **[Complete Solution](docs/COMPLETE_SOLUTION.md)**: Comprehensive overview

## 🔗 Integration Options

### 1. LibreOffice Extension (optional)

The extension is a separate embedded HTTP/UNO integration; it is not the external
MCP SDK stdio server started by `src/main.py`.

```bash
# Build and install the LibreOffice extension
cd plugin/
./install.sh install

# Test the extension
./install.sh test
```

**Extension capabilities:**
- **Real-time Editing**: Live document manipulation in open LibreOffice windows
- **Native Integration**: Appears in LibreOffice Tools menu
- **Multi-document Support**: Work with all open documents simultaneously
- **Auto-start**: Automatically starts with LibreOffice
- **Advanced Features**: Full access to LibreOffice formatting and capabilities

**Usage:**
- The extension provides an HTTP API on `http://localhost:8765`
- Configure your AI assistant to use this endpoint
- Access controls via **Tools > MCP Server** in LibreOffice
- Real-time document editing with instant visual feedback

For detailed plugin information, see [`plugin/README.md`](plugin/README.md).

### 2. Claude Desktop

Generate configuration automatically:
```bash
./generate-config.sh claude
# Creates ~/.config/claude/claude_desktop_config.json
```

Then restart Claude Desktop and start using LibreOffice commands:
- *"Create a new Writer document and save it as project-report.odt"*
- *"Convert my document to PDF format"*

### 3. Super Assistant Chrome Extension

Generate configuration and start proxy:
```bash
./generate-config.sh mcp
npx @srbhptl39/mcp-superassistant-proxy@latest --config ~/Documents/mcp/mcp.config.json
# Server URL: http://localhost:3006
```

### 4. Direct MCP Client
```python
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from libremcp import mcp

async with InMemoryTransport(mcp) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as client:
        await client.initialize()
        result = await client.call_tool("create_document", {
            "path": "/tmp/test.odt",
            "doc_type": "writer",
            "content": "Hello, World!"
        })
```

## 🎨 Usage Examples

### Natural Language (via Super Assistant)
- *"Create a new Writer document with a project report"*
- *"Convert my ODT file to PDF format"*
- *"Search for documents containing 'budget' in my Documents folder"*
- *"Get statistics for my essay - how many words?"*

### Programmatic Usage
```python
from libremcp import create_document, read_document_text, convert_document

# Create a document
doc = create_document("/tmp/report.odt", "writer", "Project Report")

# Read content
content = read_document_text("/tmp/report.odt")
print(f"Words: {content.word_count}")

# Convert to PDF
result = convert_document("/tmp/report.odt", "/tmp/report.pdf", "pdf")
```

## 📁 Supported File Formats

### Input (Reading)
- **LibreOffice**: `.odt`, `.ods`, `.odp`, `.odg`
- **Microsoft Office**: `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- **Text**: `.txt`, `.rtf`

### Output (Conversion)
- **PDF**: `.pdf`
- **Microsoft Office**: `.docx`, `.xlsx`, `.pptx`
- **Web**: `.html`, `.htm`
- **Text**: `.txt`
- **LibreOffice**: `.odt`, `.ods`, `.odp`, `.odg`
- **Many others**: 50+ formats supported by LibreOffice

## 🧪 Testing

### LibreOffice Extension Testing
```bash
# Install and test the plugin
cd plugin/
./install.sh install    # Build and install extension
./install.sh test       # Test functionality
./install.sh status     # Check status
./install.sh interactive # Interactive testing mode
```

### External Server Testing
```bash
# Show system requirements and installation guides
./mcp-helper.sh requirements

# Check dependencies and verify setup
./mcp-helper.sh check

# Run the LibreOffice smoke test
./mcp-helper.sh test

# Run the automated test suite
uv run pytest -q

# Test the real stdio protocol
uv run pytest -q tests/test_stdio_protocol.py

# Test specific functionality directly
uv run python src/main.py --test
```

The smoke test writes `test_document.odt` and, on successful export,
`test_document.pdf` to `test-output/`. The stdio test retains
`mcp-stdio-smoke.odt` there as well.

## 🔧 Configuration

### MCP Configuration for Integrations

Generate personalized configuration files for Claude Desktop and/or Super Assistant:

```bash
# Generate both Claude Desktop and Super Assistant configs
./generate-config.sh

# Generate only Claude Desktop config
./generate-config.sh claude

# Generate only Super Assistant config  
./generate-config.sh mcp

# Generate Super Assistant config in custom location
./generate-config.sh mcp /path/to/custom/directory
```

This automatically creates configurations with your actual project paths:
- **Claude Desktop**: `~/.config/claude/claude_desktop_config.json`
- **Super Assistant**: `~/Documents/mcp/mcp.config.json` (or custom location)

### Environment Variables
```bash
export PYTHONPATH="/path/to/mcp-libre"
export LIBREOFFICE_PATH="/usr/bin/libreoffice"  # Optional
```

### Custom Search Paths
Edit `libremcp.py` to modify document discovery locations:
```python
search_paths = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path("/custom/path"),
    Path.cwd()
]
```

## 🛡 Security

- **Local Execution**: All operations run locally
- **File Permissions**: Limited to user's file access
- **No Network**: No external network dependencies
- **Temporary Files**: Automatically cleaned up

## 🚨 Troubleshooting

### LibreOffice Issues
```bash
# Check LibreOffice installation
libreoffice --version
libreoffice --headless --help

# Test conversion manually in a directory LibreOffice can access
libreoffice --headless --convert-to pdf --outdir test-output document.odt
```

### Java Warnings
- Java warnings are usually non-fatal.
- Java is not required by the external MCP server or its PDF smoke test.

### Permission Errors
- Check file and directory permissions
- Ensure LibreOffice can access document paths
- Verify write permissions for output directories

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that allows:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

For other license options, see [LICENSE_OPTIONS.md](LICENSE_OPTIONS.md).

## 🔗 Links

- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **LibreOffice**: https://www.libreoffice.org/
- **MCP Python SDK 2.x**: https://py.sdk.modelcontextprotocol.io/

## 📞 Support

- **Issues**: Use GitHub issues for bug reports
- **Documentation**: See the `docs/` folder for detailed guides
- **Examples**: Check `EXAMPLES.md` for usage patterns

---

*LibreOffice MCP Server v0.1.0 - Bridging AI and Document Processing*

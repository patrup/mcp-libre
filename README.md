# LibreOffice MCP Server

A comprehensive Model Context Protocol (MCP) server that provides tools and resources for interacting with LibreOffice documents. This server enables AI assistants and other MCP clients to create, read, convert, and manipulate LibreOffice documents programmatically.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LibreOffice](https://img.shields.io/badge/LibreOffice-24.2+-green.svg)](https://www.libreoffice.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-orange.svg)](https://spec.modelcontextprotocol.io/)

## 🚀 Features

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
   git clone <repository-url>
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
# Run functionality tests
./mcp-helper.sh test

# Run interactive demo
./mcp-helper.sh demo
```

### Start MCP Server
```bash
# Standard MCP mode (stdio)
python main.py

# Or using UV
uv run python main.py
```

### Integration with Super Assistant
```bash
# Start the MCP proxy
./mcp-helper.sh proxy

# Then configure Super Assistant extension:
# Server URL: http://localhost:3000
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

## 📚 Documentation

- **[Prerequisites](PREREQUISITES.md)**: Quick reference for system requirements
- **[Examples](EXAMPLES.md)**: Code examples and usage patterns
- **[Super Assistant Setup](SUPER_ASSISTANT_SETUP.md)**: Chrome extension integration
- **[Quick Start](QUICK_START.md)**: Quick reference guide
- **[Complete Solution](COMPLETE_SOLUTION.md)**: Comprehensive overview

## 🔗 Integration Options

### 1. Claude Desktop
```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp-libre/main.py"],
      "cwd": "/path/to/mcp-libre"
    }
  }
}
```

### 2. Super Assistant Chrome Extension
```bash
npx @srbhptl39/mcp-superassistant-proxy@latest --config /path/to/mcp.config.json
```

### 3. Direct MCP Client
```python
from mcp.shared.memory import create_connected_server_and_client_session
from libremcp import mcp

async with client_session(mcp._mcp_server) as client:
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

```bash
# Show system requirements and installation guides
./mcp-helper.sh requirements

# Check dependencies and verify setup
./mcp-helper.sh check

# Run built-in functionality tests
./mcp-helper.sh test

# Interactive demo of all capabilities
./mcp-helper.sh demo

# Test specific functionality directly
uv run python libremcp.py --test
```

## 🔧 Configuration

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

# Test conversion manually
libreoffice --headless --convert-to pdf document.odt
```

### Java Warnings
- Java warnings are usually non-fatal
- Core functionality works without Java
- Install Java for full LibreOffice features

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

This project is open source. Please check the license file for details.

## 🔗 Links

- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **LibreOffice**: https://www.libreoffice.org/
- **FastMCP Framework**: https://github.com/modelcontextprotocol/python-sdk

## 📞 Support

- **Issues**: Use GitHub issues for bug reports
- **Documentation**: See the `docs/` folder for detailed guides
- **Examples**: Check `EXAMPLES.md` for usage patterns

---

*LibreOffice MCP Server v0.1.0 - Bridging AI and Document Processing*

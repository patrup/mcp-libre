# LibreOffice MCP Server + Super Assistant Chrome Extension Setup Guide

This guide explains how to use the LibreOffice MCP server with the Super Assistant Chrome extension through the MCP proxy.

## Prerequisites

1. **LibreOffice MCP Server** (already set up in `/home/patrick/work/mcp/mcp-libre/`)
2. **Super Assistant Chrome Extension** (installed in Chrome)
3. **MCP Proxy** (using `@srbhptl39/mcp-superassistant-proxy`)
4. **Node.js/NPX** (for running the proxy)

## Configuration Files

### 1. MCP Configuration (`/home/patrick/Documents/mcp/mcp.config.json`)

The configuration file has been updated to include both Blender and LibreOffice MCP servers:

```json
{
	"mcpServers": {
    	"blender": {
        	"command": "uvx",
        	"args": [
            	"blender-mcp"
        	]
    	},
    	"libreoffice": {
        	"command": "uv",
        	"args": [
            	"run",
            	"python",
            	"/home/patrick/work/mcp/mcp-libre/main.py"
        	],
        	"cwd": "/home/patrick/work/mcp/mcp-libre",
        	"env": {
            	"PYTHONPATH": "/home/patrick/work/mcp/mcp-libre"
        	}
    	}
	}
}
```

## Setup Steps

### Step 1: Start the MCP Proxy

Run the proxy server with the configuration file:

```bash
npx @srbhptl39/mcp-superassistant-proxy@latest --config /home/patrick/Documents/mcp/mcp.config.json
```

This will:
- Start the MCP proxy server (on `http://localhost:3006`)
- Load both the Blender and LibreOffice MCP servers
- Provide a bridge between the Chrome extension and the MCP servers

### Step 2: Configure Super Assistant Extension

1. Open Chrome and navigate to the Super Assistant extension
2. Configure the extension to connect to the local proxy:
   - **Server URL**: `http://localhost:3006` (or the URL shown by the proxy)
   - **API Type**: MCP or Local MCP Server
3. Save the configuration

### Step 3: Test the Connection

1. In the Super Assistant interface, you should now see LibreOffice tools available
2. Try a simple command like "List available tools" to verify connection

## Available LibreOffice Tools

Once connected, you'll have access to these LibreOffice tools through the Super Assistant:

### Document Creation & Management
- **create_document**: Create new LibreOffice documents (Writer, Calc, Impress, Draw)
- **read_document_text**: Extract text from any LibreOffice document
- **get_document_info**: Get file metadata and information
- **convert_document**: Convert between different formats (PDF, DOCX, HTML, etc.)

### Text Operations
- **insert_text_at_position**: Add, append, or replace text in documents
- **search_documents**: Find documents containing specific text
- **get_document_statistics**: Get detailed document analysis

### Spreadsheet Operations
- **read_spreadsheet_data**: Extract data from Calc spreadsheets

### Batch Operations
- **batch_convert_documents**: Convert multiple documents at once
- **merge_text_documents**: Combine multiple documents into one

### Resources
- **documents://**: Browse all LibreOffice documents in common locations
- **document://{path}**: Access specific document content

## Example Usage Through Super Assistant

Here are some example commands you can use in the Super Assistant:

### Creating Documents
```
"Create a new Writer document at /tmp/my_report.odt with the content 'This is my project report. Status: In Progress.'"
```

### Reading Documents
```
"Read the text content from /home/patrick/Documents/important_document.odt"
```

### Converting Documents
```
"Convert /home/patrick/Documents/report.odt to PDF format and save it as /home/patrick/Documents/report.pdf"
```

### Document Analysis
```
"Get detailed statistics for the document at /home/patrick/Documents/essay.odt"
```

### Searching
```
"Search for documents containing 'budget report' in the Documents folder"
```

### Batch Operations
```
"Convert all ODT files in /home/patrick/Documents/reports/ to PDF format"
```

## Troubleshooting

### Proxy Issues
1. **Port Already in Use**: If port 3000 is busy, the proxy will use another port - check the console output
2. **Configuration Errors**: Verify the JSON syntax in `mcp.config.json`
3. **Permission Issues**: Ensure the proxy has access to the MCP server directory

### LibreOffice Server Issues
1. **LibreOffice Not Found**: Ensure LibreOffice is installed and in PATH
2. **File Permission Errors**: Check read/write permissions for document directories
3. **Conversion Failures**: Some formats may not be supported or may require additional dependencies

### Extension Connection Issues
1. **CORS Errors**: The proxy should handle CORS automatically
2. **Network Issues**: Ensure firewall isn't blocking localhost connections
3. **Extension Configuration**: Double-check the server URL in extension settings

## Advanced Configuration

### Custom Timeouts
You can modify the LibreOffice server to use custom timeouts for operations:

```python
# In libremcp.py, modify the _run_libreoffice_command function
def _run_libreoffice_command(args: List[str], timeout: int = 60):  # Increased timeout
```

### Additional Environment Variables
Add environment variables to the MCP configuration for specific setups:

```json
"env": {
    "PYTHONPATH": "/home/patrick/work/mcp/mcp-libre",
    "LIBREOFFICE_PATH": "/usr/bin/libreoffice",
    "TEMP_DIR": "/tmp/mcp_libre"
}
```

### Resource Paths
Customize the document search paths by modifying the `list_documents` function in `libremcp.py`:

```python
search_paths = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path("/custom/document/path"),
    Path.cwd()
]
```

## Security Considerations

1. **Local Network Only**: The proxy runs on localhost by default
2. **File Access**: The MCP server has access to files with your user permissions
3. **Command Execution**: LibreOffice commands are executed with your user privileges
4. **Temp Files**: Temporary files are created during operations and cleaned up automatically

## Integration Benefits

Using the LibreOffice MCP server through Super Assistant provides:

1. **Natural Language Interface**: Describe what you want to do with documents
2. **Batch Processing**: Handle multiple documents efficiently
3. **Format Flexibility**: Convert between many document formats
4. **Content Analysis**: Extract insights from document collections
5. **Automation**: Integrate document processing into AI workflows
6. **Cross-Platform**: Works with various LibreOffice-supported formats

## Support & Resources

- **LibreOffice Documentation**: https://help.libreoffice.org/
- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **Project Repository**: `/home/patrick/work/mcp/mcp-libre/`
- **Test Examples**: See `EXAMPLES.md` in the project directory

## Next Steps

1. Start the proxy with the provided command
2. Configure the Super Assistant extension
3. Test basic operations like document creation and reading
4. Explore advanced features like batch conversion and document analysis
5. Integrate into your document workflow

The LibreOffice MCP server provides powerful document processing capabilities through a simple, natural language interface via the Super Assistant extension!

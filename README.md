# LibreOffice MCP Server

A Model Context Protocol (MCP) server that provides tools and resources for interacting with LibreOffice documents. This server enables AI assistants and other MCP clients to read, write, convert, and manipulate LibreOffice documents programmatically.

## Features

### Document Operations
- **Create Documents**: Create new Writer, Calc, Impress, or Draw documents
- **Read Content**: Extract text content from any LibreOffice document
- **Convert Formats**: Convert between different document formats (PDF, DOCX, TXT, etc.)
- **Edit Documents**: Insert, append, or replace text in Writer documents
- **Document Info**: Get detailed metadata about documents

### Spreadsheet Operations
- **Read Spreadsheets**: Extract data from Calc spreadsheets and Excel files
- **Data Export**: Convert spreadsheet data to structured formats

### Batch Operations
- **Batch Convert**: Convert multiple documents in a directory
- **Search Documents**: Find documents containing specific text
- **Merge Documents**: Combine multiple documents into one
- **Document Statistics**: Get detailed analytics about document content

### Resources
- **Document Discovery**: List all LibreOffice documents in common locations
- **Document Content**: Access document content through MCP resources

## Prerequisites

- **LibreOffice**: Must be installed and accessible via command line
  - On Ubuntu/Debian: `sudo apt install libreoffice`
  - On macOS: Install from [LibreOffice website](https://www.libreoffice.org/download/download/)
  - On Windows: Install from [LibreOffice website](https://www.libreoffice.org/download/download/)

- **Python 3.12+**

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   uv install
   # or
   pip install -e .
   ```

## Usage

### Running the MCP Server

The server can be run in different modes:

#### Standard MCP Server (stdio transport)
```bash
python main.py
# or
mcp-libre
```

#### Test Mode
```bash
python main.py --test
# or
python libremcp.py --test
```

### Integration with Claude Desktop

Add this configuration to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "python",
      "args": ["/path/to/mcp-libre/main.py"],
      "env": {}
    }
  }
}
```

## Available Tools

### Core Document Tools

#### `create_document(path, doc_type, content)`
Create a new LibreOffice document.
- `path`: Full path where document should be created
- `doc_type`: "writer", "calc", "impress", or "draw"
- `content`: Initial text content (for Writer documents)

#### `read_document_text(path)`
Extract text content from any LibreOffice document.
- `path`: Path to the document file

#### `convert_document(source_path, target_path, target_format)`
Convert a document to a different format.
- `source_path`: Path to source document
- `target_path`: Path for converted document
- `target_format`: Target format (pdf, docx, txt, html, etc.)

#### `get_document_info(path)`
Get detailed information about a document file.
- `path`: Path to the document

#### `insert_text_at_position(path, text, position)`
Insert text into a Writer document.
- `path`: Path to the document
- `text`: Text to insert
- `position`: "start", "end", or "replace"

### Spreadsheet Tools

#### `read_spreadsheet_data(path, sheet_name, max_rows)`
Read data from a spreadsheet.
- `path`: Path to spreadsheet file
- `sheet_name`: Specific sheet name (optional)
- `max_rows`: Maximum rows to read (default: 100)

### Utility Tools

#### `search_documents(query, search_path)`
Search for documents containing specific text.
- `query`: Text to search for
- `search_path`: Directory to search (optional)

#### `batch_convert_documents(source_dir, target_dir, target_format, source_extensions)`
Convert multiple documents in batch.
- `source_dir`: Source directory
- `target_dir`: Target directory
- `target_format`: Target format
- `source_extensions`: File extensions to convert (optional)

#### `merge_text_documents(document_paths, output_path, separator)`
Merge multiple documents into one.
- `document_paths`: List of document paths
- `output_path`: Output file path
- `separator`: Text between merged documents

#### `get_document_statistics(path)`
Get detailed statistics about a document.
- `path`: Path to the document

## Available Resources

### `documents://`
Lists all LibreOffice documents in common locations (Documents, Desktop, current directory).

### `document://{path}`
Get the text content of a specific document by path.

## Supported File Formats

### Input Formats
- LibreOffice: `.odt`, `.ods`, `.odp`, `.odg`
- Microsoft Office: `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- Text: `.txt`, `.rtf`
- And many others supported by LibreOffice

### Output Formats
- PDF: `.pdf`
- Microsoft Office: `.docx`, `.xlsx`, `.pptx`
- HTML: `.html`
- Text: `.txt`
- OpenDocument: `.odt`, `.ods`, `.odp`, `.odg`
- And many others supported by LibreOffice

## Examples

### Creating and Editing a Document
```python
# Create a new Writer document
doc_info = create_document("/tmp/my_document.odt", "writer", "Hello, World!")

# Add more content
doc_info = insert_text_at_position("/tmp/my_document.odt", "\n\nThis is additional content.", "end")

# Convert to PDF
result = convert_document("/tmp/my_document.odt", "/tmp/my_document.pdf", "pdf")
```

### Reading and Analyzing Documents
```python
# Read document content
content = read_document_text("/path/to/document.odt")
print(f"Words: {content.word_count}, Characters: {content.char_count}")

# Get detailed statistics
stats = get_document_statistics("/path/to/document.odt")
print(f"Sentences: {stats['content_stats']['sentence_count']}")
```

### Working with Spreadsheets
```python
# Read spreadsheet data
data = read_spreadsheet_data("/path/to/spreadsheet.ods", max_rows=50)
print(f"Sheet: {data.sheet_name}, Rows: {data.row_count}, Cols: {data.col_count}")
```

## Error Handling

The server includes comprehensive error handling for common scenarios:
- Missing LibreOffice installation
- File not found errors
- Unsupported file formats
- Conversion failures
- Permission issues

All errors are returned as structured responses with descriptive error messages.

## Development

### Running Tests
```bash
python main.py --test
```

### Project Structure
```
mcp-libre/
├── libremcp.py          # Main MCP server implementation
├── main.py              # Entry point
├── pyproject.toml       # Project configuration
├── README.md            # This file
└── uv.lock             # Dependency lock file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Troubleshooting

### LibreOffice Not Found
If you get "LibreOffice executable not found" errors:
1. Ensure LibreOffice is installed
2. Verify it's in your system PATH
3. Try running `libreoffice --version` in terminal

### Conversion Failures
If document conversions fail:
1. Check that the source file exists and is readable
2. Verify the target format is supported by LibreOffice
3. Ensure you have write permissions in the target directory

### Performance Issues
For large documents or batch operations:
1. Consider using smaller `max_rows` for spreadsheets
2. Use appropriate file formats for your use case
3. Monitor system resources during batch operations

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review LibreOffice documentation for format support
3. Check the MCP protocol documentation for integration help

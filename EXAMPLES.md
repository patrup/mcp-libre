# LibreOffice MCP Server - Usage Examples

This document provides practical examples of how to use the LibreOffice MCP Server.

## Basic Document Operations

### Creating Documents

```python
# Create a Writer document with content
result = create_document(
    path="/path/to/my_document.odt",
    doc_type="writer", 
    content="Hello, World!\n\nThis is my first LibreOffice document created via MCP."
)

# Create a Calc spreadsheet
result = create_document(
    path="/path/to/spreadsheet.ods",
    doc_type="calc"
)

# Create a Presentation 
result = create_document(
    path="/path/to/presentation.odp",
    doc_type="impress"
)
```

### Reading Documents

```python
# Read text content from any LibreOffice document
content = read_document_text("/path/to/document.odt")
print(f"Document has {content.word_count} words and {content.char_count} characters")
print(f"Content: {content.content}")

# Get document metadata
info = get_document_info("/path/to/document.odt")
print(f"File: {info.filename}, Size: {info.size_bytes} bytes")
print(f"Format: {info.format}, Modified: {info.modified_time}")
```

### Document Conversion

```python
# Convert ODT to PDF
result = convert_document(
    source_path="/path/to/document.odt",
    target_path="/path/to/document.pdf", 
    target_format="pdf"
)

if result.success:
    print("Conversion successful!")
else:
    print(f"Conversion failed: {result.error_message}")

# Convert to Microsoft Word format
result = convert_document(
    source_path="/path/to/document.odt",
    target_path="/path/to/document.docx",
    target_format="docx"
)

# Convert to HTML
result = convert_document(
    source_path="/path/to/document.odt", 
    target_path="/path/to/document.html",
    target_format="html"
)
```

## Advanced Operations

### Text Manipulation

```python
# Add text to the end of a document
result = insert_text_at_position(
    path="/path/to/document.odt",
    text="\n\nThis text was added to the end of the document.",
    position="end"
)

# Insert text at the beginning
result = insert_text_at_position(
    path="/path/to/document.odt", 
    text="This is a new introduction.\n\n",
    position="start"
)

# Replace entire document content
result = insert_text_at_position(
    path="/path/to/document.odt",
    text="This completely replaces the document content.",
    position="replace"
)
```

### Working with Spreadsheets

```python
# Read data from a spreadsheet
data = read_spreadsheet_data(
    path="/path/to/spreadsheet.ods",
    sheet_name="Sheet1",  # Optional
    max_rows=50          # Optional, default 100
)

print(f"Sheet: {data.sheet_name}")
print(f"Dimensions: {data.row_count} rows × {data.col_count} columns")

# Access cell data
for row_idx, row in enumerate(data.data):
    for col_idx, cell in enumerate(row):
        print(f"Cell [{row_idx}][{col_idx}]: {cell}")
```

### Document Search

```python
# Search for documents containing specific text
results = search_documents(
    query="important project",
    search_path="/home/user/Documents"  # Optional
)

for doc in results:
    print(f"Found in: {doc['filename']}")
    print(f"Path: {doc['path']}")
    print(f"Context: {doc['match_context']}")
```

### Batch Operations

```python
# Convert all documents in a directory
results = batch_convert_documents(
    source_dir="/path/to/source_documents",
    target_dir="/path/to/converted_documents", 
    target_format="pdf",
    source_extensions=[".odt", ".doc", ".docx"]  # Optional
)

for result in results:
    if result.success:
        print(f"✓ Converted {result.source_path}")
    else:
        print(f"✗ Failed to convert {result.source_path}: {result.error_message}")

# Merge multiple documents
merged_doc = merge_text_documents(
    document_paths=[
        "/path/to/doc1.odt",
        "/path/to/doc2.odt", 
        "/path/to/doc3.odt"
    ],
    output_path="/path/to/merged_document.odt",
    separator="\n\n=== DOCUMENT BREAK ===\n\n"
)
```

### Document Analysis

```python
# Get detailed statistics about a document
stats = get_document_statistics("/path/to/document.odt")

file_info = stats['file_info']
content_stats = stats['content_stats']

print(f"File: {file_info['filename']}")
print(f"Size: {file_info['size_bytes']} bytes")
print(f"Words: {content_stats['word_count']}")
print(f"Characters: {content_stats['character_count']}")
print(f"Sentences: {content_stats['sentence_count']}")
print(f"Paragraphs: {content_stats['paragraph_count']}")
print(f"Average words per sentence: {content_stats['average_words_per_sentence']:.1f}")
```

## Using Resources

The MCP server also provides resources for document discovery:

### List All Documents

```python
# Access via resource URI: documents://
# This will list all LibreOffice documents in common locations:
# - ~/Documents
# - ~/Desktop  
# - Current working directory
```

### Access Document Content

```python
# Access specific document content via resource URI: document://{path}
# Example: document://tmp/my_document.odt
# Returns formatted text content with metadata
```

## Integration Examples

### Claude Desktop Configuration

Add this to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "libreoffice": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp-libre/main.py"],
      "cwd": "/path/to/mcp-libre",
      "env": {
        "PYTHONPATH": "/path/to/mcp-libre"
      }
    }
  }
}
```

### Common Use Cases

1. **Document Processing Pipeline**
   - Create documents from templates
   - Insert generated content
   - Convert to multiple formats for distribution

2. **Content Analysis**
   - Extract text from various document formats
   - Analyze document statistics
   - Search across document collections

3. **Batch Document Management**
   - Convert legacy documents to modern formats
   - Merge related documents
   - Generate reports from multiple sources

4. **Integration with AI Workflows**
   - Process documents for AI analysis
   - Generate summaries and insights
   - Create formatted reports from AI-generated content

## Error Handling

The server provides detailed error messages for common issues:

- **File not found**: Clear error message with file path
- **Conversion failures**: LibreOffice error output included
- **Permission issues**: System-level error details
- **Format not supported**: List of supported formats

Always check the `success` field in conversion results and handle errors appropriately in your applications.

## Performance Considerations

- **Large documents**: Text extraction may take time for very large files
- **Batch operations**: Process documents in smaller batches for better performance
- **Spreadsheet data**: Use `max_rows` parameter to limit data size
- **Concurrent operations**: The server handles one operation at a time

## Troubleshooting

1. **LibreOffice not found**: Ensure LibreOffice is installed and in your PATH
2. **Java warnings**: These are usually non-fatal; core functionality will still work
3. **Permission errors**: Check file and directory permissions
4. **Conversion failures**: Verify target format is supported by LibreOffice

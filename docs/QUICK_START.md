# 🚀 Quick Start: LibreOffice MCP + Super Assistant

## Setup Commands (Run in Terminal)

1. **Install dependencies and check the environment:**
   ```bash
   cd <PATH_TO>/mcp-libre
   uv sync
   <PATH_TO>/mcp-libre/mcp-helper.sh check
   ```

2. **Run the automated and stdio tests:**
   ```bash
   uv run pytest -q
   uv run pytest -q tests/test_stdio_protocol.py
   ```

3. **Run the LibreOffice smoke test or start the proxy:**
   ```bash
   uv run python src/main.py --test
   <PATH_TO>/mcp-libre/mcp-helper.sh proxy
   ```

## Super Assistant Extension Configuration

- **Server URL**: `http://localhost:3006`
- **Type**: MCP Server / Local MCP
- **Authentication**: None (local server)

## Quick Commands to Try in Super Assistant

### 📝 Document Creation
- *"Create a new Writer document with a project status report"*
- *"Create a spreadsheet for tracking expenses"*

### 📖 Reading Documents  
- *"Read the content from my document at ~/Documents/report.odt"*
- *"What are the statistics for the document at ~/Desktop/essay.odt?"*

### 🔄 Format Conversion
- *"Convert my ODT file to PDF format"*
- *"Convert all Word documents in my Documents folder to LibreOffice format"*

### 🔍 Document Search
- *"Find all documents containing the word 'budget' in my Documents folder"*
- *"Search for documents with 'meeting notes' in them"*

### ✏️ Text Editing
- *"Add a conclusion paragraph to my document"*
- *"Insert a header at the beginning of my report"*

### 📊 Spreadsheet Operations
- *"Read the data from the first 20 rows of my spreadsheet"*
- *"Show me the contents of Sheet1 from my expenses.ods file"*

## Available Tools Summary

| Tool | Description | Example Use |
|------|-------------|-------------|
| `create_document` | Create new documents | "Create a presentation about AI" |
| `read_document_text` | Extract text from docs | "Read my contract.odt file" |
| `convert_document` | Change file formats | "Convert to PDF" |
| `insert_text_at_position` | Edit document text | "Add a summary at the end" |
| `read_spreadsheet_data` | Get spreadsheet data | "Show me the budget data" |
| `search_documents` | Find docs by content | "Find files about project X" |
| `batch_convert_documents` | Convert multiple files | "Convert all docs to PDF" |
| `merge_text_documents` | Combine documents | "Merge all reports into one" |
| `get_document_statistics` | Analyze document | "How many words in my essay?" |

## File Paths You Can Use

- **Home Directory**: `~/` or `/home/username/`
- **Documents**: `~/Documents/` or `/home/username/Documents/`
- **Desktop**: `~/Desktop/` or `/home/username/Desktop/`
- **Temp Files**: `/tmp/` (for testing)

## Supported File Formats

### Input Formats (Can Read From)
- LibreOffice: `.odt`, `.ods`, `.odp`, `.odg`
- Microsoft Office: `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`
- Text: `.txt`, `.rtf`

### Output Formats (Can Convert To)
- PDF: `.pdf`
- Microsoft Office: `.docx`, `.xlsx`, `.pptx`
- Web: `.html`, `.htm`
- Text: `.txt`
- LibreOffice: `.odt`, `.ods`, `.odp`, `.odg`

## Troubleshooting

### If Proxy Won't Start
```bash
# Check if port 3000 is free
sudo netstat -tulpn | grep :3000

# Kill any process using port 3000
sudo fuser -k 3000/tcp
```

### If LibreOffice Commands Fail
```bash
# Test LibreOffice directly
libreoffice --version
libreoffice --headless --help
```

### If Super Assistant Can't Connect
1. Make sure proxy is running (`mcp-helper.sh proxy`)
2. Check Chrome allows localhost connections
3. Verify Super Assistant settings use `http://localhost:3006`

## Need Help?

- **Run Demo**: `<PATH_TO>/mcp-libre/mcp-helper.sh demo`
- **View Config**: `<PATH_TO>/mcp-libre/mcp-helper.sh config`
- **Full Documentation**: See `SUPER_ASSISTANT_SETUP.md`

---

💡 **Pro Tip**: Start with simple commands like "Create a test document" to verify everything works, then try more complex operations!

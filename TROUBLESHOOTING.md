# Troubleshooting Guide - LibreOffice MCP Server

## Common Issues and Solutions

### ❌ Error: "Document conversion failed"

**Problem**: When trying to insert text (especially simple characters like "."), you get:
```
Error executing tool insert_text_at_position: Failed to insert text: Document conversion failed
```

**✅ Solution**: This has been fixed in the latest version! The issue was caused by an overly complex document modification process.

**What was changed**:
- Improved `insert_text_at_position` function with robust document handling
- Added proper ODT file creation using valid ZIP structure
- Better error handling and fallback mechanisms

**To verify the fix works**:
```bash
# Run the test script
uv run python test_insert_fix.py

# Or test specific functionality
./mcp-helper.sh test
```

### ❌ Error: "LibreOffice executable not found"

**Problem**: 
```
Error: LibreOffice executable not found
```

**✅ Solutions**:
1. **Install LibreOffice**:
   ```bash
   # Ubuntu/Debian
   sudo apt install libreoffice
   
   # macOS
   brew install --cask libreoffice
   
   # Check installation
   libreoffice --version
   ```

2. **Verify PATH**:
   ```bash
   which libreoffice
   # Should show path like /usr/bin/libreoffice
   ```

3. **Check headless mode**:
   ```bash
   libreoffice --headless --help
   ```

### ❌ Error: "Failed to read document: File is not a zip file"

**Problem**: Document appears corrupted or invalid.

**✅ Solutions**:
1. **Check file integrity**:
   ```bash
   file /path/to/document.odt
   # Should show: "OpenDocument Text"
   ```

2. **Recreate the document**:
   ```bash
   # Use the MCP server to create a new document
   # Then copy content from the corrupted one
   ```

3. **Use LibreOffice to repair**:
   ```bash
   libreoffice --headless --convert-to odt --outdir /tmp corrupted_file.odt
   ```

### ❌ Error: "Permission denied"

**Problem**: Cannot read or write to document files.

**✅ Solutions**:
1. **Check file permissions**:
   ```bash
   ls -la /path/to/document.odt
   chmod 644 /path/to/document.odt  # Make readable/writable
   ```

2. **Check directory permissions**:
   ```bash
   ls -la /path/to/directory/
   chmod 755 /path/to/directory/  # Make accessible
   ```

### ❌ Error: "Java warnings" or "PDF conversion failed"

**Problem**: 
```
Warning: failed to launch javaldx - java may not function correctly
Error: source file could not be loaded
```

**✅ Solutions**:
1. **Install Java** (optional but recommended):
   ```bash
   # Ubuntu/Debian
   sudo apt install default-jre
   
   # macOS
   brew install openjdk
   
   # Verify
   java -version
   ```

2. **Continue without Java**: Basic functionality works without Java, only PDF generation may be limited.

### ❌ Error: "MCP server not responding"

**Problem**: Claude Desktop or Super Assistant can't connect to the MCP server.

**✅ Solutions**:

1. **For Claude Desktop**:
   ```bash
   # Check your claude_config.json path
   cat ~/.config/claude/claude_desktop_config.json
   
   # Verify the server path is correct
   ls -la <PATH_TO>/mcp-libre/main.py
   ```

2. **For Super Assistant**:
   ```bash
   # Start the proxy
   ./mcp-helper.sh proxy
   
   # Check if it's running
   curl http://localhost:3006/health
   ```

3. **Test the server directly**:
   ```bash
   # Run basic tests
   ./mcp-helper.sh test
   
   # Test specific functionality
   uv run python -c "from libremcp import create_document; print('Server working!')"
   ```

## Diagnostic Commands

### Check System Requirements
```bash
./mcp-helper.sh check
```

### Test All Functionality
```bash
./mcp-helper.sh test
```

### Show System Information
```bash
./mcp-helper.sh info
```

### View Detailed Requirements
```bash
./mcp-helper.sh requirements
```

### Test Insert Function Specifically
```bash
uv run python test_insert_fix.py
```

## Debug Mode

To get more detailed error information:

1. **Run server with debug output**:
   ```bash
   PYTHONPATH=<PATH_TO>/mcp-libre uv run python main.py --verbose
   ```

2. **Check LibreOffice directly**:
   ```bash
   libreoffice --headless --convert-to pdf --outdir /tmp test.odt
   ```

3. **Verify document structure**:
   ```bash
   # For ODT files (they're ZIP archives)
   unzip -l document.odt
   ```

## Getting Help

1. **Check the documentation**:
   - [README.md](README.md)
   - [EXAMPLES.md](EXAMPLES.md)
   - [CHATGPT_BROWSER_GUIDE.md](CHATGPT_BROWSER_GUIDE.md)

2. **Run diagnostics**:
   ```bash
   ./mcp-helper.sh check
   ./mcp-helper.sh test
   ```

3. **Test with simple operations**:
   ```bash
   # Create a test document
   uv run python -c "
   from libremcp import create_document
   result = create_document('/tmp/test.odt', 'writer', 'Hello World')
   print(f'Created: {result.path}')
   "
   ```

## Common Fixes Summary

| Error | Quick Fix |
|-------|-----------|
| Document conversion failed | ✅ Fixed in latest version |
| LibreOffice not found | Install LibreOffice, check PATH |
| Permission denied | Fix file/directory permissions |
| Java warnings | Install Java (optional) |
| MCP not responding | Check config, restart proxy |
| File not zip | Document corrupted, recreate |

## Prevention Tips

1. **Keep backups** of important documents
2. **Test changes** on copies first
3. **Check permissions** before bulk operations
4. **Update regularly** to get latest fixes
5. **Use absolute paths** in configurations

---

*Last updated: After fixing the insert_text_at_position issue*

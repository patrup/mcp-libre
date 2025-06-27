# Live Viewing in LibreOffice with MCP Server

## Overview

The LibreOffice MCP Server supports **live viewing** - seeing your document changes in real-time as you modify them through AI assistants like Claude Desktop. This creates a seamless workflow where you can watch your documents update live while giving natural language commands.

## 🎯 Live Viewing Options

### 1. Basic Live Viewing

**Open a document in LibreOffice GUI while editing via MCP:**

```bash
# Via Claude Desktop
"Open my document.odt in LibreOffice for live viewing"

# Via Super Assistant  
"Start a live editing session with my report.docx"
```

### 2. Advanced Live Session

**Create a full live editing session with automatic refresh:**

```bash
# Create comprehensive live session
"Create a live editing session for my presentation.odp"
```

### 3. Change Monitoring

**Watch documents for changes in real-time:**

```bash
# Monitor document changes
"Watch my document for changes for 60 seconds"

# Detect file modifications
"Monitor my spreadsheet for updates"
```

## 🛠 Available Tools

### `open_document_in_libreoffice(path, readonly=False)`
Opens a document in LibreOffice GUI for live viewing.

**Example:**
```python
# Open for editing
open_document_in_libreoffice("/path/to/document.odt")

# Open read-only
open_document_in_libreoffice("/path/to/document.odt", readonly=True)
```

### `create_live_editing_session(path, auto_refresh=True)`
Creates a complete live editing environment.

**Features:**
- Opens document in LibreOffice GUI
- Sets up automatic change detection
- Provides session management
- Includes usage instructions

### `refresh_document_in_libreoffice(path)`
Forces LibreOffice to refresh and reload the document.

**Use when:**
- Changes don't appear automatically
- Need to sync after MCP modifications
- Want to ensure latest version is displayed

### `watch_document_changes(path, duration_seconds=30)`
Monitors a document for changes and reports them.

**Returns:**
- Change timestamps
- File size differences
- Modification details
- Real-time updates

## 🚀 Workflow Examples

### Example 1: Writing a Report with Live Preview

1. **Start the session:**
   ```
   Claude: "Create a live editing session for my report.odt"
   ```

2. **Watch it open in LibreOffice GUI**

3. **Make changes via Claude:**
   ```
   You: "Add an introduction paragraph about AI integration"
   Claude: *modifies document*
   ```

4. **See changes live in LibreOffice**
   - LibreOffice detects file changes
   - Prompts to reload (or auto-reloads)
   - You see the new content immediately

### Example 2: Collaborative Document Review

1. **Open document for viewing:**
   ```
   "Open my contract.odt in read-only mode"
   ```

2. **Make suggestions via MCP:**
   ```
   "Add a comment about section 3"
   "Insert a clause about liability"
   ```

3. **Watch changes live:**
   ```
   "Watch the document for 5 minutes while I make changes"
   ```

### Example 3: Presentation Development

1. **Live session for slides:**
   ```
   "Create a live editing session for my presentation.odp"
   ```

2. **Real-time slide creation:**
   ```
   "Add a slide about market analysis"
   "Insert a chart showing growth trends"
   "Add speaker notes to slide 3"
   ```

3. **Preview immediately in Impress**

## 🔄 How Live Updates Work

### Automatic Detection
- **File modification time**: LibreOffice monitors file timestamps
- **Change notifications**: OS file system events trigger updates
- **Auto-refresh**: LibreOffice prompts or automatically reloads

### Manual Refresh
- **Keyboard shortcut**: `Ctrl+Shift+R` in LibreOffice
- **Menu option**: File → Reload
- **MCP command**: Use `refresh_document_in_libreoffice()`

### Bidirectional Changes
- **MCP → LibreOffice**: Changes via AI commands appear in GUI
- **LibreOffice → MCP**: Manual edits can be detected and reported

## 💡 Best Practices

### 1. Document Management
```bash
# Always start with a live session for extended editing
"Create a live editing session for my document"

# Use refresh when changes don't appear
"Refresh my document in LibreOffice"  

# Monitor during collaborative work
"Watch my document for changes while others edit"
```

### 2. Performance Optimization
- **Close unused documents** to reduce memory usage
- **Use read-only mode** when just reviewing
- **Monitor selectively** (don't watch continuously for hours)

### 3. Error Recovery
```bash
# If document appears corrupted
"Refresh my document in LibreOffice"

# If LibreOffice becomes unresponsive  
"Open my document again in LibreOffice"

# If changes are lost
"Read the current content of my document"
```

## 🎮 Demo and Testing

### Run the Live Viewing Demo
```bash
# Comprehensive demonstration
uv run python demo_live_viewing.py

# Quick test of live features
./mcp-helper.sh demo
```

### Test Individual Features
```bash
# Test document opening
uv run python -c "
from libremcp import open_document_in_libreoffice
result = open_document_in_libreoffice('/path/to/test.odt')
print(result)
"

# Test change monitoring
uv run python -c "
from libremcp import watch_document_changes  
result = watch_document_changes('/path/to/test.odt', 10)
print(result)
"
```

## ⚙️ Configuration Options

### LibreOffice Settings
For optimal live viewing experience:

1. **Enable auto-reload**:
   - Tools → Options → Load/Save → General
   - Check "Always create backup copy"
   - Set "AutoRecover" to 1 minute

2. **Configure file monitoring**:
   - Tools → Options → LibreOffice → Advanced  
   - Enable "Experimental features"
   - May improve change detection

### System Settings
```bash
# Increase file watch limits (Linux)
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf

# Optimize for frequent file changes
echo vm.dirty_expire_centisecs=500 | sudo tee -a /etc/sysctl.conf
```

## 🔧 Troubleshooting Live Viewing

### Document Doesn't Open
- **Check file path**: Ensure absolute path is correct
- **Verify permissions**: Make sure file is readable
- **LibreOffice running**: Close existing instances if needed

### Changes Don't Appear
- **Manual refresh**: Press `Ctrl+Shift+R` in LibreOffice
- **Use refresh tool**: `refresh_document_in_libreoffice()`
- **Check file locks**: Ensure document isn't locked by another process

### Performance Issues
- **Close unused documents**: Reduce memory usage
- **Limit watch duration**: Don't monitor for extended periods
- **Use read-only mode**: When not editing directly

### File Corruption
- **Refresh document**: May resolve temporary issues  
- **Recreate from backup**: Use LibreOffice auto-backup
- **Use MCP to recreate**: Extract content and recreate document

## 🌟 Advanced Use Cases

### 1. Real-time Documentation
```bash
"Create a live session for my documentation.odt"
"Add a section about the new feature"
"Insert code examples with syntax highlighting"
"Update the table of contents"
```

### 2. Interactive Presentations
```bash
"Open my presentation.odp for live editing"
"Add a slide about quarterly results"  
"Insert animations for the new slide"
"Preview the presentation flow"
```

### 3. Collaborative Review
```bash
"Open the contract.odt in read-only mode"
"Watch for changes while the legal team reviews"
"Add comments based on their feedback"
"Track all modifications for the record"
```

### 4. Document Automation
```bash
"Create a live session for my report template"
"Fill in the quarterly data automatically"
"Generate charts from the spreadsheet data"
"Format the document for professional presentation"
```

## 📚 Integration with AI Assistants

### Claude Desktop Commands
- *"Open my document for live viewing"*
- *"Start a live editing session"*  
- *"Make changes while I watch in LibreOffice"*
- *"Refresh the document display"*

### Super Assistant Commands
- *"Begin live document editing"*
- *"Monitor document changes"*
- *"Update document with real-time preview"*
- *"Sync changes with LibreOffice"*

---

**Live viewing transforms document editing from a blind process into an interactive, visual experience where you can see your AI assistant's work in real-time!** 🚀

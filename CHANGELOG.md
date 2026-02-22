# Changelog

## [1.4.0] - 2026-02-20

### Added
- `insert_image` tool — insert image with optional caption frame, anchor at paragraph
- `delete_image` tool — remove image and parent frame; `remove_frame=false` keeps frame (for replacement)
- `replace_image` tool — swap image source in-place, keeps frame/position/caption; optional proportional resize
- `goto_page` tool — scroll LibreOffice view to a given page number
- `get_page_objects` now returns **frames** with image mapping (frame → contained images)
- `AGENT.md`: Page Object Indexing Strategy, Text Frames workflow, image tools reference

### Changed
- Renamed project "LibreOffice MCP Server" → "LibreOffice MCP"

### Fixed
- UNO proxy identity: replaced Python `id()` with UNO `==` operator in `delete_image`, `list_text_frames`, `get_page_objects` — fixes frame-image detection

## [1.3.1] - 2026-02-20

### Added
- **Page proximity**: `get_page_objects(locator=...|paragraph_index=...)` — find images/tables near a paragraph by page
- `get_document_tree` now includes page numbers per heading and `page_count`
- `close_document` tool across all layers (UNO bridge, HTTP, MCP)
- `search_documents` now searches only open documents by default (fast, no side effects); pass `search_path` to scan disk

### Changed
- `open_document` duplicate detection: exact URL match reuses document; same filename at different path shows warning instead of blocking
- `open_document` accepts `force` parameter to always open in new frame

### Fixed
- Normalized URL comparison in `_find_open_document` (lowercase, URL-decoded) prevents false negatives on Windows

## [1.3.0] - 2026-02-20

### Added
- **Main thread executor**: all UNO calls run on LO main thread via `AsyncCallback` — fixes black menus and crashes on large docs
- **59 tools** registered in plugin (was 24)
- Comments & review: `list_comments`, `add_comment`, `resolve_comment`, `delete_comment`
- Track changes: `set_track_changes`, `get_tracked_changes`, `accept_all_changes`, `reject_all_changes`
- Styles: `list_styles`, `get_style_info`
- Writer tables: `list_tables`, `read_table`, `write_table_cell`, `create_table`
- Images: `list_images`, `get_image_info`, `set_image_properties` (resize, anchor, title/alt-text)
- Paragraph editing: `set_paragraph_text`, `delete_paragraph`, `duplicate_paragraph`, `set_paragraph_style`
- Document management: `save_document`, `save_document_copy`, `refresh_indexes`, `update_fields`, `get_document_properties`, `set_document_properties`
- Document protection: `set_document_protection` (UI lock via ProtectForm, UNO passes through)
- Recent documents: `get_recent_documents` (reads LO history)
- `list_open_documents`, `open_document` tools
- `AGENT.md` — agent guide with workflow, anti-patterns, tool reference
- `DEVEL.md` — developer guide with architecture, scripts, env vars, pitfalls

### Changed
- Renamed `setup-windows.ps1` → `install.ps1` with `-Plugin` and `-BuildOnly` flags
- Moved all helper scripts to `scripts/` directory
- Restructured `src/` into `server.py`, `plugin.py`, `backends/`, `tools/` (was single `libremcp.py`)
- Plugin version read from `version.py` (single source of truth)

### Fixed
- UNO enum serialization in `get_image_info` (AnchorType, HoriOrient, VertOrient)
- Recent documents config path (`/org.openoffice.Office.Histories/Histories/PickList/ItemList`)
- `$PSScriptRoot` resolution in scripts moved to `scripts/` subdirectory

## [1.2.0] - 2026-02-20

### Added
- All MCP tools now work in GUI mode via plugin HTTP API
- Tools `create_document`, `read_document_text`, `convert_document`, `read_spreadsheet_data`, `insert_text_at_position`, `open_document_in_libreoffice`, `refresh_document_in_libreoffice` delegate to plugin when `MCP_LIBREOFFICE_GUI=1`

### Fixed
- "LibreOffice is already running" error when using MCP tools in GUI mode

## [1.1.3] - 2026-02-20

### Added
- Dynamic menu icons (play/stop/hourglass) based on server state
- Live-updating Server Status dialog with async health probe
- Dev workflow with junction symlink (`dev-deploy.ps1`)
- Version displayed in logs and About dialog
- Native LibreOffice Options dialog for config
- Auto-restart on config change

### Fixed
- Menu graying out during server startup
- Icons not showing on first menu display
- Slow Server Status dialog (now async)

## [1.0.0] - 2025-06-28

### Added
- LibreOffice plugin/extension with embedded HTTP server
- Context-efficient document tools (heading tree, paragraphs, search, bookmarks)
- AI annotation system for document headings
- Live viewing and document management tools

## [0.1.0] - 2025-06-27

### Added
- Initial MCP server with document CRUD operations
- Writer, Calc, Impress, Draw support
- Document conversion, search, batch operations
- Configuration generator for Claude Desktop

"""
Writer tools — locator-aware tools for Writer documents.
Replaces plugin_tools.py. All tools delegate to the LO plugin via call_plugin().
Path is optional — omit it to use the active document.
"""

from typing import Any, Callable, Dict, List, Optional


def _p(params: Dict[str, Any], path: Optional[str]) -> Dict[str, Any]:
    """Add file_path only when a path was given."""
    if path is not None:
        params["file_path"] = path
    return params


def register(mcp, call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]):

    @mcp.tool()
    def get_document_tree(path: Optional[str] = None,
                          content_strategy: str = "first_lines",
                          depth: int = 1) -> Dict[str, Any]:
        """Get the heading tree of a document without loading full text.

        Returns headings organized as a tree. Use depth to control how many
        levels are returned (1=top-level only, 2=two levels, 0=full tree).
        Use content_strategy to control body text visibility:
        none, first_lines, ai_summary_first, full.

        Args:
            path: Absolute path to the document (optional, uses active doc)
            content_strategy: What to show for body text (default: first_lines)
            depth: Heading levels to return (default: 1)
        """
        return call_plugin("get_document_tree", _p({
            "content_strategy": content_strategy, "depth": depth}, path))

    @mcp.tool()
    def get_heading_children(path: Optional[str] = None,
                             locator: Optional[str] = None,
                             heading_para_index: Optional[int] = None,
                             heading_bookmark: Optional[str] = None,
                             content_strategy: str = "first_lines",
                             depth: int = 1) -> Dict[str, Any]:
        """Drill down into a heading to see its children.

        Use locator for unified addressing (e.g. 'bookmark:_mcp_x',
        'heading:2.1', 'paragraph:5'). Legacy params heading_bookmark
        and heading_para_index are still supported.

        Args:
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator string (preferred)
            heading_para_index: Paragraph index of the parent heading (legacy)
            heading_bookmark: Bookmark name (legacy)
            content_strategy: none, first_lines, ai_summary_first, full
            depth: Sub-levels to include (default: 1)
        """
        params: Dict[str, Any] = {
            "content_strategy": content_strategy, "depth": depth}
        if locator is not None:
            params["locator"] = locator
        if heading_bookmark is not None:
            params["heading_bookmark"] = heading_bookmark
        if heading_para_index is not None:
            params["heading_para_index"] = heading_para_index
        return call_plugin("get_heading_children", _p(params, path))

    @mcp.tool()
    def read_document_paragraphs(path: Optional[str] = None,
                                 locator: Optional[str] = None,
                                 start_index: Optional[int] = None,
                                 count: int = 10) -> Dict[str, Any]:
        """Read specific paragraphs by locator or index range.

        Use get_document_tree first to find which paragraphs to read.
        Locator examples: 'paragraph:0', 'page:2', 'bookmark:_mcp_x',
        'section:Introduction'.

        Args:
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator string (e.g. 'paragraph:0', 'page:2')
            start_index: Zero-based index of first paragraph (legacy)
            count: Number of paragraphs to read (default: 10)
        """
        params: Dict[str, Any] = {"count": count}
        if locator is not None:
            params["locator"] = locator
        if start_index is not None:
            params["start_index"] = start_index
        return call_plugin("read_paragraphs", _p(params, path))

    @mcp.tool()
    def get_document_paragraph_count(path: Optional[str] = None) -> Dict[str, Any]:
        """Get total paragraph count of a document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_paragraph_count", _p({}, path))

    @mcp.tool()
    def search_in_document(pattern: str, path: Optional[str] = None,
                           regex: bool = False,
                           case_sensitive: bool = False,
                           max_results: int = 20,
                           context_paragraphs: int = 1) -> Dict[str, Any]:
        """Search for text in a document with paragraph context.

        Uses LibreOffice native search. Returns matches with surrounding
        paragraphs for context, without loading the entire document.

        Args:
            pattern: Search string or regex
            path: Absolute path to the document (optional, uses active doc)
            regex: Use regular expression (default: False)
            case_sensitive: Case-sensitive search (default: False)
            max_results: Max results to return (default: 20)
            context_paragraphs: Paragraphs of context around each match (default: 1)
        """
        return call_plugin("search_in_document", _p({
            "pattern": pattern, "regex": regex,
            "case_sensitive": case_sensitive, "max_results": max_results,
            "context_paragraphs": context_paragraphs}, path))

    @mcp.tool()
    def replace_in_document(search: str, replace: str,
                            path: Optional[str] = None,
                            regex: bool = False,
                            case_sensitive: bool = False) -> Dict[str, Any]:
        """Find and replace text preserving all formatting.

        Args:
            search: Text to find
            replace: Replacement text
            path: Absolute path to the document (optional, uses active doc)
            regex: Use regular expression (default: False)
            case_sensitive: Case-sensitive matching (default: False)
        """
        return call_plugin("replace_in_document", _p({
            "search": search, "replace": replace,
            "regex": regex, "case_sensitive": case_sensitive}, path))

    @mcp.tool()
    def insert_text_at_paragraph(text: str,
                                 path: Optional[str] = None,
                                 locator: Optional[str] = None,
                                 paragraph_index: Optional[int] = None,
                                 position: str = "after",
                                 style: Optional[str] = None) -> Dict[str, Any]:
        """Insert text before or after a specific paragraph.

        Preserves all existing formatting. Use locator for unified
        addressing (e.g. 'paragraph:5', 'bookmark:_mcp_x').

        Args:
            text: Text to insert
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator string (preferred)
            paragraph_index: Target paragraph index (legacy)
            position: 'before' or 'after' (default: after)
            style: Paragraph style for the new paragraph (e.g. 'Text Body',
                   'Heading 1'). If omitted, inherits from adjacent paragraph.
        """
        params: Dict[str, Any] = {"text": text, "position": position}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        if style is not None:
            params["style"] = style
        return call_plugin("insert_at_paragraph", _p(params, path))

    @mcp.tool()
    def insert_paragraphs_batch(paragraphs: List[Dict[str, str]],
                                path: Optional[str] = None,
                                locator: Optional[str] = None,
                                paragraph_index: Optional[int] = None,
                                position: str = "after") -> Dict[str, Any]:
        """Insert multiple paragraphs in one call.

        Each item in paragraphs is {"text": "...", "style": "..."}.
        Style is optional — if omitted, inherits from adjacent paragraph.
        All paragraphs are inserted in a single UNO transaction.

        Args:
            paragraphs: List of {text, style?} objects to insert
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator string (preferred)
            paragraph_index: Target paragraph index (legacy)
            position: 'before' or 'after' (default: after)
        """
        params: Dict[str, Any] = {
            "paragraphs": paragraphs, "position": position}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("insert_paragraphs_batch", _p(params, path))

    @mcp.tool()
    def add_document_ai_summary(summary: str,
                                path: Optional[str] = None,
                                locator: Optional[str] = None,
                                para_index: Optional[int] = None) -> Dict[str, Any]:
        """Add an AI annotation/summary to a heading.

        The summary is stored as a Writer annotation with Author='MCP-AI'.
        It will be shown when using content_strategy='ai_summary_first'.

        Args:
            summary: Summary text to attach
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5', 'heading:2.1')
            para_index: Paragraph index of the heading (legacy)
        """
        params: Dict[str, Any] = {"summary": summary}
        if locator is not None:
            params["locator"] = locator
        if para_index is not None:
            params["para_index"] = para_index
        return call_plugin("add_ai_summary", _p(params, path))

    @mcp.tool()
    def get_document_ai_summaries(path: Optional[str] = None) -> Dict[str, Any]:
        """List all AI annotations in a document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_ai_summaries", _p({}, path))

    @mcp.tool()
    def remove_document_ai_summary(path: Optional[str] = None,
                                   locator: Optional[str] = None,
                                   para_index: Optional[int] = None) -> Dict[str, Any]:
        """Remove an AI annotation from a heading.

        Args:
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5')
            para_index: Paragraph index of the heading (legacy)
        """
        params: Dict[str, Any] = {}
        if locator is not None:
            params["locator"] = locator
        if para_index is not None:
            params["para_index"] = para_index
        return call_plugin("remove_ai_summary", _p(params, path))

    @mcp.tool()
    def list_document_sections(path: Optional[str] = None) -> Dict[str, Any]:
        """List all named text sections in a document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_sections", _p({}, path))

    @mcp.tool()
    def read_document_section(section_name: str,
                              path: Optional[str] = None) -> Dict[str, Any]:
        """Read the content of a named text section.

        Args:
            section_name: Name of the section
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("read_section", _p({
            "section_name": section_name}, path))

    @mcp.tool()
    def list_document_bookmarks(path: Optional[str] = None) -> Dict[str, Any]:
        """List all bookmarks in a document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_bookmarks", _p({}, path))

    @mcp.tool()
    def resolve_document_bookmark(bookmark_name: str,
                                  path: Optional[str] = None) -> Dict[str, Any]:
        """Resolve a heading bookmark to its current paragraph index.

        Bookmarks are stable identifiers that survive document edits.
        Use this to find the current position of a previously bookmarked heading.

        Args:
            bookmark_name: Bookmark name (e.g. _mcp_a1b2c3d4)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("resolve_bookmark", _p({
            "bookmark_name": bookmark_name}, path))

    @mcp.tool()
    def get_document_page_count(path: Optional[str] = None) -> Dict[str, Any]:
        """Get the page count of a document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_page_count", _p({}, path))

    @mcp.tool()
    def goto_page(page: int,
                  path: Optional[str] = None) -> Dict[str, Any]:
        """Scroll the LibreOffice view to a specific page.

        Use this to visually navigate to a page so the user can see it.

        Args:
            page: Page number (1-based)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("goto_page", _p({"page": page}, path))

    @mcp.tool()
    def get_page_objects(page: Optional[int] = None,
                         locator: Optional[str] = None,
                         paragraph_index: Optional[int] = None,
                         path: Optional[str] = None) -> Dict[str, Any]:
        """Get images and tables on a page.

        Pass page number directly, OR a locator/paragraph_index to
        resolve the page automatically. Use this to find objects near
        a paragraph or comment.

        Args:
            page: Page number (1-based)
            locator: Locator to resolve page from (e.g. 'paragraph:89')
            paragraph_index: Paragraph index to resolve page from
            path: Absolute path to the document (optional, uses active doc)
        """
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("get_page_objects", _p(params, path))

    # ---------------------------------------------------------------
    # Document maintenance
    # ---------------------------------------------------------------

    @mcp.tool()
    def refresh_document_indexes(path: Optional[str] = None) -> Dict[str, Any]:
        """Refresh all document indexes (Table of Contents, alphabetical, etc.).

        Call this after modifying headings or text referenced by indexes.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("refresh_indexes", _p({}, path))

    @mcp.tool()
    def update_document_fields(path: Optional[str] = None) -> Dict[str, Any]:
        """Refresh all text fields (dates, page numbers, cross-references).

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("update_fields", _p({}, path))

    @mcp.tool()
    def delete_document_paragraph(path: Optional[str] = None,
                                  locator: Optional[str] = None,
                                  paragraph_index: Optional[int] = None
                                  ) -> Dict[str, Any]:
        """Delete a paragraph from the document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5', 'bookmark:_mcp_x')
            paragraph_index: Paragraph index (legacy)
        """
        params: Dict[str, Any] = {}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("delete_paragraph", _p(params, path))

    @mcp.tool()
    def set_document_paragraph_text(text: str,
                                    path: Optional[str] = None,
                                    locator: Optional[str] = None,
                                    paragraph_index: Optional[int] = None
                                    ) -> Dict[str, Any]:
        """Replace the entire text of a paragraph (preserves style).

        Args:
            text: New text content for the paragraph
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5', 'bookmark:_mcp_x')
            paragraph_index: Paragraph index (legacy)
        """
        params: Dict[str, Any] = {"text": text}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("set_paragraph_text", _p(params, path))

    @mcp.tool()
    def set_document_paragraph_style(style_name: str,
                                     path: Optional[str] = None,
                                     locator: Optional[str] = None,
                                     paragraph_index: Optional[int] = None
                                     ) -> Dict[str, Any]:
        """Set the paragraph style (e.g. 'Heading 1', 'Text Body', 'List Bullet').

        Args:
            style_name: Name of the paragraph style to apply
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5', 'bookmark:_mcp_x')
            paragraph_index: Paragraph index (legacy)
        """
        params: Dict[str, Any] = {"style_name": style_name}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("set_paragraph_style", _p(params, path))

    @mcp.tool()
    def duplicate_document_paragraph(path: Optional[str] = None,
                                     locator: Optional[str] = None,
                                     paragraph_index: Optional[int] = None,
                                     count: int = 1) -> Dict[str, Any]:
        """Duplicate a paragraph (with its style) after itself.

        Use count > 1 to duplicate a block (e.g. heading + body paragraphs).

        Args:
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5', 'bookmark:_mcp_x')
            paragraph_index: Paragraph index (legacy)
            count: Number of consecutive paragraphs to duplicate (default: 1)
        """
        params: Dict[str, Any] = {"count": count}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("duplicate_paragraph", _p(params, path))

    @mcp.tool()
    def get_document_metadata(path: Optional[str] = None) -> Dict[str, Any]:
        """Read document metadata (title, author, subject, keywords, dates).

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_document_properties", _p({}, path))

    @mcp.tool()
    def set_document_metadata(path: Optional[str] = None,
                              title: Optional[str] = None,
                              author: Optional[str] = None,
                              subject: Optional[str] = None,
                              description: Optional[str] = None,
                              keywords: Optional[list] = None
                              ) -> Dict[str, Any]:
        """Update document metadata (title, author, subject, etc.).

        Args:
            path: Absolute path to the document (optional, uses active doc)
            title: Document title
            author: Document author
            subject: Document subject
            description: Document description
            keywords: List of keywords
        """
        params: Dict[str, Any] = {}
        if title is not None:
            params["title"] = title
        if author is not None:
            params["author"] = author
        if subject is not None:
            params["subject"] = subject
        if description is not None:
            params["description"] = description
        if keywords is not None:
            params["keywords"] = keywords
        return call_plugin("set_document_properties", _p(params, path))

    @mcp.tool()
    def save_document_copy(target_path: str,
                           path: Optional[str] = None) -> Dict[str, Any]:
        """Save/duplicate a document under a new name.

        Creates a copy of the document at the target path.

        Args:
            target_path: New file path to save the copy to
            path: Source document (optional, uses active doc)
        """
        return call_plugin("save_document_as", _p({
            "target_path": target_path}, path))

    @mcp.tool()
    def save_active_document(path: Optional[str] = None) -> Dict[str, Any]:
        """Save the currently active document to its current location.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("save_document_live", _p({}, path))

    @mcp.tool()
    def list_open_documents_live() -> Dict[str, Any]:
        """List all currently open documents in LibreOffice."""
        return call_plugin("list_open_documents", {})

    # ---------------------------------------------------------------
    # Document Protection
    # ---------------------------------------------------------------

    @mcp.tool()
    def set_document_protection(enabled: bool,
                                path: Optional[str] = None
                                ) -> Dict[str, Any]:
        """Lock or unlock the document for human editing.

        When locked (enabled=True), the document UI becomes read-only —
        the human cannot accidentally edit while the agent is working.
        All MCP/UNO calls still work normally through the protection.
        No password — just a boolean toggle (ProtectForm setting).

        Call with enabled=False when the agent is done, so the human
        can resume manual editing.

        Args:
            enabled: True to lock (human can't edit), False to unlock
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("set_document_protection", _p({
            "enabled": enabled}, path))

    # ---------------------------------------------------------------
    # Comments
    # ---------------------------------------------------------------

    @mcp.tool()
    def list_document_comments(path: Optional[str] = None) -> Dict[str, Any]:
        """List all comments/annotations in the document.

        Returns human comments (excludes MCP-AI summaries). Each comment
        includes author, content, resolved status, paragraph index, and
        whether it's a reply.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_comments", _p({}, path))

    @mcp.tool()
    def add_document_comment(content: str,
                             author: str = "AI Agent",
                             path: Optional[str] = None,
                             locator: Optional[str] = None,
                             paragraph_index: Optional[int] = None
                             ) -> Dict[str, Any]:
        """Add a comment at a paragraph.

        Args:
            content: Comment text
            author: Author name (default: AI Agent)
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator (e.g. 'paragraph:5', 'bookmark:_mcp_x')
            paragraph_index: Paragraph index (legacy)
        """
        params: Dict[str, Any] = {"content": content, "author": author}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("add_comment", _p(params, path))

    @mcp.tool()
    def resolve_document_comment(comment_name: str,
                                 resolution: str = "",
                                 author: str = "AI Agent",
                                 path: Optional[str] = None
                                 ) -> Dict[str, Any]:
        """Resolve a comment with an optional reason.

        Adds a reply with the resolution text, then marks as resolved.
        Use list_document_comments to find comment names.

        Args:
            comment_name: Name/ID of the comment to resolve
            resolution: Reason for resolution (e.g. 'Done: updated age to 14')
            author: Author of the resolution (default: AI Agent)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("resolve_comment", _p({
            "comment_name": comment_name, "resolution": resolution,
            "author": author}, path))

    @mcp.tool()
    def delete_document_comment(comment_name: str,
                                path: Optional[str] = None
                                ) -> Dict[str, Any]:
        """Delete a comment and all its replies.

        Args:
            comment_name: Name/ID of the comment to delete
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("delete_comment", _p({
            "comment_name": comment_name}, path))

    # ---------------------------------------------------------------
    # Track Changes
    # ---------------------------------------------------------------

    @mcp.tool()
    def set_document_track_changes(enabled: bool,
                                   path: Optional[str] = None
                                   ) -> Dict[str, Any]:
        """Enable or disable change tracking (record changes).

        Enable before making edits so the human can review diffs.
        Disable after changes are accepted.

        Args:
            enabled: True to enable tracking, False to disable
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("set_track_changes", _p({
            "enabled": enabled}, path))

    @mcp.tool()
    def get_document_tracked_changes(path: Optional[str] = None
                                     ) -> Dict[str, Any]:
        """List all tracked changes (redlines) in the document.

        Returns change type, author, date, and comment for each redline.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_tracked_changes", _p({}, path))

    @mcp.tool()
    def accept_all_document_changes(path: Optional[str] = None
                                    ) -> Dict[str, Any]:
        """Accept all tracked changes in the document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("accept_all_changes", _p({}, path))

    @mcp.tool()
    def reject_all_document_changes(path: Optional[str] = None
                                    ) -> Dict[str, Any]:
        """Reject all tracked changes in the document.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("reject_all_changes", _p({}, path))

    # ---------------------------------------------------------------
    # Styles
    # ---------------------------------------------------------------

    @mcp.tool()
    def list_document_styles(family: str = "ParagraphStyles",
                             path: Optional[str] = None
                             ) -> Dict[str, Any]:
        """List available styles in a family.

        Use this to discover which styles exist before applying them.
        Filter by is_in_use to see what the document actually uses.

        Args:
            family: ParagraphStyles, CharacterStyles, PageStyles,
                    FrameStyles, NumberingStyles (default: ParagraphStyles)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_styles", _p({
            "family": family}, path))

    @mcp.tool()
    def get_document_style_info(style_name: str,
                                family: str = "ParagraphStyles",
                                path: Optional[str] = None
                                ) -> Dict[str, Any]:
        """Get detailed properties of a style (font, size, margins, etc.).

        Args:
            style_name: Name of the style
            family: Style family (default: ParagraphStyles)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_style_info", _p({
            "style_name": style_name, "family": family}, path))

    # ---------------------------------------------------------------
    # Writer Tables
    # ---------------------------------------------------------------

    @mcp.tool()
    def list_document_tables(path: Optional[str] = None
                             ) -> Dict[str, Any]:
        """List all text tables in a Writer document.

        Returns table name, row count, and column count for each table.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_tables", _p({}, path))

    @mcp.tool()
    def read_document_table(table_name: str,
                            path: Optional[str] = None
                            ) -> Dict[str, Any]:
        """Read all cell contents from a Writer table.

        Returns a 2D array of cell values.

        Args:
            table_name: Name of the table (use list_document_tables to find)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("read_table", _p({
            "table_name": table_name}, path))

    @mcp.tool()
    def write_document_table_cell(table_name: str, cell: str,
                                  value: str,
                                  path: Optional[str] = None
                                  ) -> Dict[str, Any]:
        """Write to a cell in a Writer table.

        Numbers are auto-detected. Use cell addresses like A1, B3, etc.

        Args:
            table_name: Name of the table
            cell: Cell address (e.g. 'A1', 'B3')
            value: Value to write
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("write_table_cell", _p({
            "table_name": table_name, "cell": cell, "value": value}, path))

    @mcp.tool()
    def create_document_table(rows: int, cols: int,
                              path: Optional[str] = None,
                              locator: Optional[str] = None,
                              paragraph_index: Optional[int] = None
                              ) -> Dict[str, Any]:
        """Create a new table at a paragraph position.

        The table is inserted after the target paragraph.

        Args:
            rows: Number of rows
            cols: Number of columns
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator for insertion point
            paragraph_index: Paragraph index (legacy)
        """
        params: Dict[str, Any] = {"rows": rows, "cols": cols}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("create_table", _p(params, path))

    # ---------------------------------------------------------------
    # Images
    # ---------------------------------------------------------------

    @mcp.tool()
    def list_document_images(path: Optional[str] = None
                             ) -> Dict[str, Any]:
        """List all images/graphic objects in the document.

        Returns name, dimensions, title, and description for each image.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_images", _p({}, path))

    @mcp.tool()
    def get_document_image_info(image_name: str,
                                path: Optional[str] = None
                                ) -> Dict[str, Any]:
        """Get detailed info about a specific image.

        Returns URL, dimensions, anchor type, orientation, and paragraph index.

        Args:
            image_name: Name of the image/graphic object
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_image_info", _p({
            "image_name": image_name}, path))

    @mcp.tool()
    def set_document_image_properties(image_name: str,
                                      width_mm: Optional[int] = None,
                                      height_mm: Optional[int] = None,
                                      title: Optional[str] = None,
                                      description: Optional[str] = None,
                                      anchor_type: Optional[int] = None,
                                      hori_orient: Optional[int] = None,
                                      vert_orient: Optional[int] = None,
                                      hori_orient_relation: Optional[int] = None,
                                      vert_orient_relation: Optional[int] = None,
                                      crop_top_mm: Optional[int] = None,
                                      crop_bottom_mm: Optional[int] = None,
                                      crop_left_mm: Optional[int] = None,
                                      crop_right_mm: Optional[int] = None,
                                      path: Optional[str] = None
                                      ) -> Dict[str, Any]:
        """Resize, reposition, crop, or update caption/alt-text for an image.

        Provide width_mm alone to resize keeping aspect ratio.
        Provide both width_mm and height_mm to set exact dimensions.

        Anchor types:
          0 = AT_PARAGRAPH (default, flows with paragraph)
          1 = AS_CHARACTER (inline, like a big character)
          2 = AT_PAGE (fixed position on page)
          4 = AT_CHARACTER (anchored to a character position)

        Orientation:
          HoriOrient: 0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT
          VertOrient: 0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM

        Orient relation (what the orient is relative to):
          0=PARAGRAPH, 1=FRAME, 2=PAGE...

        Crop: values in mm, trims the image without resizing.

        Args:
            image_name: Name of the image (use list_document_images to find)
            width_mm: New width in millimeters
            height_mm: New height in millimeters
            title: Image title / caption text
            description: Alt-text for accessibility
            anchor_type: Anchor type (0, 1, 2, or 4)
            hori_orient: Horizontal orientation
            vert_orient: Vertical orientation
            hori_orient_relation: Horizontal orient relative to (0=PARAGRAPH, 1=FRAME)
            vert_orient_relation: Vertical orient relative to (0=PARAGRAPH, 1=FRAME)
            crop_top_mm: Crop from top in mm
            crop_bottom_mm: Crop from bottom in mm
            crop_left_mm: Crop from left in mm
            crop_right_mm: Crop from right in mm
            path: Absolute path to the document (optional, uses active doc)
        """
        params: Dict[str, Any] = {"image_name": image_name}
        if width_mm is not None:
            params["width_mm"] = width_mm
        if height_mm is not None:
            params["height_mm"] = height_mm
        if title is not None:
            params["title"] = title
        if description is not None:
            params["description"] = description
        if anchor_type is not None:
            params["anchor_type"] = anchor_type
        if hori_orient is not None:
            params["hori_orient"] = hori_orient
        if vert_orient is not None:
            params["vert_orient"] = vert_orient
        if hori_orient_relation is not None:
            params["hori_orient_relation"] = hori_orient_relation
        if vert_orient_relation is not None:
            params["vert_orient_relation"] = vert_orient_relation
        if crop_top_mm is not None:
            params["crop_top_mm"] = crop_top_mm
        if crop_bottom_mm is not None:
            params["crop_bottom_mm"] = crop_bottom_mm
        if crop_left_mm is not None:
            params["crop_left_mm"] = crop_left_mm
        if crop_right_mm is not None:
            params["crop_right_mm"] = crop_right_mm
        return call_plugin("set_image_properties", _p(params, path))

    @mcp.tool()
    def insert_document_image(image_path: str,
                              path: Optional[str] = None,
                              locator: Optional[str] = None,
                              paragraph_index: Optional[int] = None,
                              caption: Optional[str] = None,
                              with_frame: bool = True,
                              width_mm: Optional[int] = None,
                              height_mm: Optional[int] = None
                              ) -> Dict[str, Any]:
        """Insert an image from a file path into the document.

        By default the image is wrapped in a text frame (caption frame).
        Set with_frame=False to insert a standalone image.
        If caption is provided, it is added as text below the image
        inside the frame.

        Args:
            image_path: Absolute path to the image file on disk
            path: Absolute path to the document (optional, uses active doc)
            locator: Unified locator for insertion point (e.g. 'paragraph:5')
            paragraph_index: Paragraph index to insert after (legacy)
            caption: Caption text below the image (optional)
            with_frame: Wrap in a text frame (default: True)
            width_mm: Width in mm (default: 80)
            height_mm: Height in mm (default: 80)
        """
        params: Dict[str, Any] = {
            "image_path": image_path, "with_frame": with_frame}
        if locator is not None:
            params["locator"] = locator
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        if caption is not None:
            params["caption"] = caption
        if width_mm is not None:
            params["width_mm"] = width_mm
        if height_mm is not None:
            params["height_mm"] = height_mm
        return call_plugin("insert_image", _p(params, path))

    @mcp.tool()
    def delete_document_image(image_name: str,
                              remove_frame: bool = True,
                              path: Optional[str] = None
                              ) -> Dict[str, Any]:
        """Delete an image from the document.

        If the image is inside a text frame and remove_frame=True (default),
        the entire frame (image + caption) is removed.
        Set remove_frame=False to remove only the image while keeping
        the frame and its caption intact.

        Args:
            image_name: Name of the image (use list_document_images to find)
            remove_frame: Also remove parent frame (default: True)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("delete_image", _p({
            "image_name": image_name,
            "remove_frame": remove_frame}, path))

    @mcp.tool()
    def replace_document_image(image_name: str,
                               new_image_path: str,
                               width_mm: Optional[int] = None,
                               height_mm: Optional[int] = None,
                               path: Optional[str] = None
                               ) -> Dict[str, Any]:
        """Replace an image's source file, keeping its frame and position.

        The image stays in its current frame with the same anchor,
        orientation, and caption. Only the graphic source changes.
        Optionally resize after replacement.

        Args:
            image_name: Name of the image to replace
            new_image_path: Absolute path to the new image file on disk
            width_mm: New width in mm (optional, keeps current if omitted)
            height_mm: New height in mm (optional, keeps current if omitted)
            path: Absolute path to the document (optional, uses active doc)
        """
        params: Dict[str, Any] = {
            "image_name": image_name,
            "new_image_path": new_image_path}
        if width_mm is not None:
            params["width_mm"] = width_mm
        if height_mm is not None:
            params["height_mm"] = height_mm
        return call_plugin("replace_image", _p(params, path))

    # ---------------------------------------------------------------
    # Text Frames
    # ---------------------------------------------------------------

    @mcp.tool()
    def list_document_frames(path: Optional[str] = None
                             ) -> Dict[str, Any]:
        """List all text frames in the document.

        Returns name, dimensions, anchor type, orientation, paragraph_index,
        and contained images for each frame.

        Args:
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("list_text_frames", _p({}, path))

    @mcp.tool()
    def get_document_frame_info(frame_name: str,
                                path: Optional[str] = None
                                ) -> Dict[str, Any]:
        """Get detailed info about a specific text frame.

        Returns size, position, anchor type, orientation, wrap mode,
        paragraph_index, contained text (caption), and contained images.

        Args:
            frame_name: Name of the text frame (use list_document_frames)
            path: Absolute path to the document (optional, uses active doc)
        """
        return call_plugin("get_text_frame_info", _p({
            "frame_name": frame_name}, path))

    @mcp.tool()
    def set_document_frame_properties(frame_name: str,
                                      width_mm: Optional[int] = None,
                                      height_mm: Optional[int] = None,
                                      anchor_type: Optional[int] = None,
                                      hori_orient: Optional[int] = None,
                                      vert_orient: Optional[int] = None,
                                      hori_pos_mm: Optional[int] = None,
                                      vert_pos_mm: Optional[int] = None,
                                      wrap: Optional[int] = None,
                                      paragraph_index: Optional[int] = None,
                                      path: Optional[str] = None
                                      ) -> Dict[str, Any]:
        """Modify text frame properties (size, position, wrap, anchor).

        Orientation values:
          HoriOrient: 0=NONE, 1=RIGHT, 2=CENTER, 3=LEFT
          VertOrient: 0=NONE, 1=TOP, 2=CENTER, 3=BOTTOM

        Wrap values: 0=NONE, 1=COLUMN, 2=PARALLEL, 3=DYNAMIC, 4=THROUGH

        Anchor types:
          0 = AT_PARAGRAPH, 1 = AS_CHARACTER, 2 = AT_PAGE, 4 = AT_CHARACTER

        Args:
            frame_name: Name of the frame (use list_document_frames to find)
            width_mm: New width in millimeters
            height_mm: New height in millimeters
            anchor_type: Anchor type (0, 1, 2, or 4)
            hori_orient: Horizontal orientation
            vert_orient: Vertical orientation
            hori_pos_mm: Horizontal position in mm (when hori_orient=NONE)
            vert_pos_mm: Vertical position in mm (when vert_orient=NONE)
            wrap: Text wrap mode
            paragraph_index: Move anchor to this paragraph index
            path: Absolute path to the document (optional, uses active doc)
        """
        params: Dict[str, Any] = {"frame_name": frame_name}
        if width_mm is not None:
            params["width_mm"] = width_mm
        if height_mm is not None:
            params["height_mm"] = height_mm
        if anchor_type is not None:
            params["anchor_type"] = anchor_type
        if hori_orient is not None:
            params["hori_orient"] = hori_orient
        if vert_orient is not None:
            params["vert_orient"] = vert_orient
        if hori_pos_mm is not None:
            params["hori_pos_mm"] = hori_pos_mm
        if vert_pos_mm is not None:
            params["vert_pos_mm"] = vert_pos_mm
        if wrap is not None:
            params["wrap"] = wrap
        if paragraph_index is not None:
            params["paragraph_index"] = paragraph_index
        return call_plugin("set_text_frame_properties", _p(params, path))

    # ---------------------------------------------------------------
    # Recent Documents
    # ---------------------------------------------------------------

    @mcp.tool()
    def get_recent_documents(max_count: int = 20) -> Dict[str, Any]:
        """Get the list of recently opened documents from LO history.

        Returns file paths and titles of recently opened documents.
        Useful to quickly find and open a document without knowing its path.

        Args:
            max_count: Maximum number of documents to return (default: 20)
        """
        return call_plugin("get_recent_documents", {
            "max_count": max_count})

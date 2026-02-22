"""
Common tools — document operations that work across all document types.
Fuses the former document_tools, composite_tools, and live_tools modules.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..backends.base import DocumentBackend
from ..models import (
    DocumentInfo, TextContent, ConversionResult, SpreadsheetData,
    get_document_info,
)


_AGENT_MD = Path(__file__).resolve().parent.parent.parent / "AGENT.md"


def register(mcp, backend: DocumentBackend,
             call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]):

    # ---------------------------------------------------------------
    # Agent cheat sheet
    # ---------------------------------------------------------------

    @mcp.tool()
    def get_agent_guide() -> str:
        """Get the agent cheat sheet: quick rules, decision tree, locator guide, workflows, and do/don't table.

        Call this first if you are unsure how to use the LibreOffice MCP tools.
        """
        try:
            return _AGENT_MD.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "AGENT.md not found. See https://github.com/quazardous/mcp-libre"

    # ---------------------------------------------------------------
    # Document CRUD (from document_tools)
    # ---------------------------------------------------------------

    @mcp.tool()
    def create_document(path: str, doc_type: str = "writer",
                        content: str = "") -> DocumentInfo:
        """Create a new LibreOffice document

        Args:
            path: Full path where the document should be created
            doc_type: Type of document to create (writer, calc, impress, draw)
            content: Initial content for the document (for writer documents)
        """
        return backend.create_document(path, doc_type, content)

    @mcp.tool()
    def read_document_text(path: str) -> TextContent:
        """Extract text content from a LibreOffice document

        Args:
            path: Path to the document file
        """
        return backend.read_document_text(path)

    @mcp.tool()
    def convert_document(source_path: str, target_path: str,
                         target_format: str) -> ConversionResult:
        """Convert a document to a different format

        Args:
            source_path: Path to the source document
            target_path: Path where converted document should be saved
            target_format: Target format (pdf, docx, xlsx, pptx, html, txt, etc.)
        """
        return backend.convert_document(source_path, target_path, target_format)

    @mcp.tool(name="get_document_info")
    def get_document_info_tool(path: str) -> DocumentInfo:
        """Get detailed information about a LibreOffice document

        Args:
            path: Path to the document file
        """
        return get_document_info(path)

    @mcp.tool()
    def insert_text_at_position(path: str, text: str,
                                position: str = "end") -> DocumentInfo:
        """Insert text into a LibreOffice Writer document

        Args:
            path: Path to the document file
            text: Text to insert
            position: Where to insert the text ("start", "end", or "replace")
        """
        return backend.insert_text(path, text, position)

    @mcp.tool()
    def read_spreadsheet_data(path: str, sheet_name: Optional[str] = None,
                              max_rows: int = 100) -> SpreadsheetData:
        """Read data from a LibreOffice Calc spreadsheet (legacy tool)

        Args:
            path: Path to the spreadsheet file (.ods, .xlsx, etc.)
            sheet_name: Name of the specific sheet to read (if None, reads first sheet)
            max_rows: Maximum number of rows to read (default 100)
        """
        return backend.read_spreadsheet_data(path, sheet_name, max_rows)

    # ---------------------------------------------------------------
    # Composite tools (from composite_tools)
    # ---------------------------------------------------------------

    @mcp.tool()
    def search_documents(query: str,
                         search_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for documents containing specific text.

        By default searches only documents already open in LibreOffice (fast,
        no side effects).  Pass ``search_path`` to also scan a directory on
        disk — already-open docs are searched via LibreOffice, other files
        are searched with a plain-text read (no GUI windows are opened).

        Args:
            query: Text to search for
            search_path: Directory to scan on disk (default: search open documents only)
        """
        results: List[Dict[str, Any]] = []

        # Default: search open documents via plugin
        if not search_path:
            try:
                open_docs = call_plugin("list_open_documents", {})
                for doc in open_docs.get("documents", []):
                    try:
                        matches = call_plugin("search_in_document", {
                            "pattern": query,
                            "file_path": doc.get("url", ""),
                            "max_results": 5,
                            "context_paragraphs": 1,
                        })
                        if matches.get("matches"):
                            previews = [m.get("match_text", "")
                                        for m in matches["matches"][:3]]
                            results.append({
                                "path": doc.get("url", ""),
                                "filename": doc.get("title", ""),
                                "type": doc.get("type", ""),
                                "word_count": doc.get("word_count", 0),
                                "match_count": matches.get("total_matches", 0),
                                "matches": previews,
                            })
                    except Exception:
                        continue
            except Exception:
                pass
            return results

        # Explicit path: scan filesystem without opening docs in the GUI.
        # Already-open docs are searched via the LO plugin; other files are
        # searched with a simple text-based read (no GUI side-effects).
        search_dir = Path(search_path)
        if not search_dir.exists():
            return results

        extensions = {'.odt', '.ods', '.odp', '.odg', '.doc', '.docx', '.txt'}

        # Build a set of file URLs that are already open in LO.
        open_urls: set = set()
        try:
            open_docs = call_plugin("list_open_documents", {})
            for doc in open_docs.get("documents", []):
                open_urls.add(doc.get("url", ""))
        except Exception:
            pass

        for ext in extensions:
            for doc_path in search_dir.rglob(f'*{ext}'):
                if not doc_path.is_file():
                    continue
                file_url = doc_path.resolve().as_uri()

                if file_url in open_urls:
                    # Document is already open — search via the LO plugin.
                    try:
                        matches = call_plugin("search_in_document", {
                            "pattern": query,
                            "file_path": str(doc_path),
                            "max_results": 5,
                            "context_paragraphs": 1,
                        })
                        if matches.get("matches"):
                            previews = [m.get("match_text", "")
                                        for m in matches["matches"][:3]]
                            results.append({
                                "path": str(doc_path),
                                "filename": doc_path.name,
                                "format": doc_path.suffix.lower(),
                                "match_count": matches.get("total_matches", 0),
                                "matches": previews,
                            })
                    except Exception:
                        pass
                else:
                    # Document is NOT open — use a plain-text grep so we
                    # never pop up a window.  Only works for .txt files;
                    # binary office formats are silently skipped.
                    try:
                        text = doc_path.read_text(errors="ignore")
                    except Exception:
                        continue
                    if query.lower() in text.lower():
                        ctx = _get_match_context(text, query)
                        results.append({
                            "path": str(doc_path),
                            "filename": doc_path.name,
                            "format": doc_path.suffix.lower(),
                            "match_count": text.lower().count(query.lower()),
                            "matches": [ctx] if ctx else [],
                        })
        return results

    @mcp.tool()
    def batch_convert_documents(source_dir: str, target_dir: str,
                                target_format: str,
                                source_extensions: Optional[List[str]] = None
                                ) -> List[ConversionResult]:
        """Convert multiple documents in a directory to a different format

        Args:
            source_dir: Directory containing source documents
            target_dir: Directory where converted documents should be saved
            target_format: Target format for conversion
            source_extensions: List of source file extensions to convert (default: common formats)
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)

        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        target_path.mkdir(parents=True, exist_ok=True)

        if source_extensions is None:
            source_extensions = [
                '.odt', '.ods', '.odp', '.doc', '.docx',
                '.xls', '.xlsx', '.ppt', '.pptx']

        results: List[ConversionResult] = []
        for ext in source_extensions:
            for doc_file in source_path.rglob(f'*{ext}'):
                if doc_file.is_file():
                    target_file = target_path / f"{doc_file.stem}.{target_format}"
                    results.append(backend.convert_document(
                        str(doc_file), str(target_file), target_format))
        return results

    @mcp.tool()
    def merge_text_documents(document_paths: List[str], output_path: str,
                             separator: str = "\n\n---\n\n") -> DocumentInfo:
        """Merge multiple text documents into a single document

        Args:
            document_paths: List of paths to documents to merge
            output_path: Path where merged document should be saved
            separator: Text to insert between merged documents
        """
        merged: List[str] = []
        for doc_path in document_paths:
            try:
                content = backend.read_document_text(doc_path)
                merged.append(
                    f"=== {Path(doc_path).name} ===\n\n{content.content}")
            except Exception as e:
                merged.append(
                    f"=== {Path(doc_path).name} ===\n\n"
                    f"Error reading document: {e}")

        return backend.create_document(
            output_path, "writer", separator.join(merged))

    @mcp.tool()
    def get_document_statistics(path: str) -> Dict[str, Any]:
        """Get detailed statistics about a document

        Args:
            path: Path to the document file
        """
        doc_info = get_document_info(path)
        if not doc_info.exists:
            raise FileNotFoundError(f"Document not found: {path}")

        try:
            content = backend.read_document_text(path)
            lines = content.content.split('\n')
            paragraphs = [p for p in content.content.split('\n\n')
                          if p.strip()]
            sentences = [s for s in content.content
                         .replace('!', '.').replace('?', '.').split('.')
                         if s.strip()]
            return {
                "file_info": doc_info.model_dump(),
                "content_stats": {
                    "word_count": content.word_count,
                    "character_count": content.char_count,
                    "line_count": len(lines),
                    "paragraph_count": len(paragraphs),
                    "sentence_count": len(sentences),
                    "average_words_per_sentence":
                        content.word_count / max(len(sentences), 1),
                    "average_chars_per_word":
                        content.char_count / max(content.word_count, 1),
                },
            }
        except Exception as e:
            return {
                "file_info": doc_info.model_dump(),
                "error": f"Could not analyze content: {e}",
            }

    # ---------------------------------------------------------------
    # Live tools (from live_tools)
    # ---------------------------------------------------------------

    @mcp.tool()
    def open_document_in_libreoffice(path: str,
                                     readonly: bool = False,
                                     force: bool = False) -> Dict[str, Any]:
        """Open a document in LibreOffice GUI for live viewing

        Args:
            path: Path to the document to open
            readonly: Whether to open in read-only mode (default: False)
            force: Force open even if a document with the same name is already open
        """
        return backend.open_document(path, readonly, force=force)

    @mcp.tool()
    def refresh_document_in_libreoffice(path: str) -> Dict[str, Any]:
        """Send a refresh signal to LibreOffice to reload a document

        Args:
            path: Path to the document that should be refreshed
        """
        return backend.refresh_document(path)

    @mcp.tool()
    def watch_document_changes(path: str,
                               duration_seconds: int = 30) -> Dict[str, Any]:
        """Watch a document for changes and provide live updates

        Args:
            path: Path to the document to watch
            duration_seconds: How long to watch for changes (default: 30 seconds)
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        initial_stat = path_obj.stat()
        initial_size = initial_stat.st_size
        initial_mtime = initial_stat.st_mtime

        start = time.time()
        changes: list = []

        while time.time() - start < duration_seconds:
            try:
                cur = path_obj.stat()
                if cur.st_mtime > initial_mtime or cur.st_size != initial_size:
                    changes.append({
                        "timestamp": datetime.now().isoformat(),
                        "size_before": initial_size,
                        "size_after": cur.st_size,
                        "size_change": cur.st_size - initial_size,
                        "modification_time":
                            datetime.fromtimestamp(cur.st_mtime).isoformat(),
                    })
                    initial_size = cur.st_size
                    initial_mtime = cur.st_mtime
                time.sleep(1)
            except FileNotFoundError:
                break

        return {
            "success": True,
            "path": str(path_obj.absolute()),
            "watch_duration": duration_seconds,
            "changes_detected": len(changes),
            "changes": changes,
            "message": (f"Watched {path_obj.name} for {duration_seconds}s, "
                        f"detected {len(changes)} changes"),
        }

    @mcp.tool()
    def create_live_editing_session(path: str,
                                    auto_refresh: bool = True) -> Dict[str, Any]:
        """Create a live editing session with automatic refresh capabilities

        Args:
            path: Path to the document for live editing
            auto_refresh: Whether to enable automatic refresh detection
        """
        path_obj = Path(path)
        open_result = backend.open_document(str(path_obj), readonly=False)

        session_info: Dict[str, Any] = {
            "session_id": f"live_session_{int(time.time())}",
            "document_path": str(path_obj.absolute()),
            "document_name": path_obj.name,
            "opened_in_gui": open_result["success"],
            "auto_refresh_enabled": auto_refresh,
            "created_at": datetime.now().isoformat(),
            "instructions": {
                "view_changes": "Document is open in LibreOffice GUI",
                "make_mcp_changes": "Use insert_text_at_position, convert_document, etc.",
                "see_updates": "LibreOffice will detect file changes and prompt to reload",
                "manual_refresh": "Press Ctrl+Shift+R in LibreOffice to force reload",
                "end_session": "Close LibreOffice window when done",
            },
        }
        if auto_refresh:
            session_info["monitoring"] = (
                "File modification time will be updated after MCP operations")
        return session_info


def _get_match_context(content: str, query: str,
                       context_chars: int = 200) -> str:
    pos = content.lower().find(query.lower())
    if pos == -1:
        return ""
    start = max(0, pos - context_chars // 2)
    end = min(len(content), pos + len(query) + context_chars // 2)
    ctx = content[start:end]
    if start > 0:
        ctx = "..." + ctx
    if end < len(content):
        ctx = ctx + "..."
    return ctx

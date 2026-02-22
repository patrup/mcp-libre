"""
LibreOffice MCP — orchestrator.

Creates the FastMCP instance, initialises the backend, registers all tools
and resources, and exposes ``main()`` as the entry point.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

from mcp.server.fastmcp import FastMCP

from .plugin import call_plugin
from .backends import get_backend
from .tools import register_all


def _default_search_paths() -> List[Path]:
    """Return OS-appropriate default document directories."""
    if sys.platform == "win32":
        # %USERPROFILE%\Documents and Desktop
        home = Path.home()
        return [home / "Documents", home / "Desktop"]

    if sys.platform == "darwin":
        home = Path.home()
        return [home / "Documents", home / "Desktop"]

    # Linux / other — honour XDG user dirs when available.
    paths: List[Path] = []
    for xdg_key in ("DOCUMENTS", "DESKTOP"):
        try:
            out = subprocess.check_output(
                ["xdg-user-dir", xdg_key],
                text=True, timeout=2,
            ).strip()
            if out:
                paths.append(Path(out))
        except Exception:
            pass
    if not paths:
        home = Path.home()
        paths = [home / "Documents", home / "Desktop"]
    return paths

# ---------------------------------------------------------------------------
# FastMCP instance + backend
# ---------------------------------------------------------------------------

mcp = FastMCP("LibreOffice MCP")
backend = get_backend(call_plugin)

# ---------------------------------------------------------------------------
# Register all tools
# ---------------------------------------------------------------------------

register_all(mcp, backend, call_plugin)

# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("documents://")
def list_documents() -> List[str]:
    """List all LibreOffice documents in common locations.

    Honour the ``MCP_SEARCH_PATH`` environment variable (colon-separated
    directories on Linux/macOS, semicolon-separated on Windows).  When the
    variable is not set, fall back to OS-typical default directories.
    """
    documents: List[str] = []

    env_path = os.environ.get("MCP_SEARCH_PATH", "").strip()
    if env_path:
        sep = ";" if sys.platform == "win32" else ":"
        search_paths = [Path(p) for p in env_path.split(sep) if p.strip()]
    else:
        search_paths = _default_search_paths()

    extensions = {
        '.odt', '.ods', '.odp', '.odg',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    }
    for sp in search_paths:
        if sp.exists():
            for ext in extensions:
                for doc in sp.rglob(f'*{ext}'):
                    if doc.is_file():
                        documents.append(str(doc))
    return sorted(documents)


@mcp.resource("document://{path}")
def get_document_content(path: str) -> str:
    """Get the text content of a document that is already open in LibreOffice.

    If the document is not currently open, returns an informational message
    instead of opening it in the GUI.  Use ``open_document_in_libreoffice``
    to explicitly open a document first.
    """
    try:
        actual_path = path if path.startswith('/') else '/' + path
        path_obj = Path(actual_path)

        # Check whether the document is already open in LibreOffice.
        file_url = path_obj.resolve().as_uri()
        try:
            open_docs = call_plugin("list_open_documents", {})
            open_urls = {
                doc.get("url", "") for doc in open_docs.get("documents", [])
            }
        except Exception:
            open_urls = set()

        if file_url not in open_urls:
            return (
                f"Document '{path_obj.name}' is not currently open in "
                f"LibreOffice.  Use the open_document_in_libreoffice tool "
                f"to open it first."
            )

        content = backend.read_document_text(actual_path)
        return (f"Document: {path_obj.name}\n"
                f"Words: {content.word_count}, "
                f"Characters: {content.char_count}\n\n"
                + content.content)
    except Exception as e:
        return f"Error reading document {path}: {e}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the LibreOffice MCP server."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--help", "-h"):
            print("LibreOffice MCP")
            print("=" * 30)
            print("Usage:")
            print("  python src/main.py        # Start MCP server (stdio)")
            print("  python src/main.py --help  # Show this help")
            return
        if arg == "--version":
            print("LibreOffice MCP v1.0.0")
            return

    print("Starting LibreOffice MCP...", file=sys.stderr)
    print("Running in MCP protocol mode (stdio)", file=sys.stderr)

    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nLibreOffice MCP stopped", file=sys.stderr)
    except Exception as e:
        print(f"\nServer error: {e}", file=sys.stderr)
        sys.exit(1)

"""
Impress tools — presentation-specific tools via call_plugin().
Path is optional — omit it to use the active document.
"""

from typing import Any, Callable, Dict, Optional


def _p(params: Dict[str, Any], path: Optional[str]) -> Dict[str, Any]:
    """Add file_path only when a path was given."""
    if path is not None:
        params["file_path"] = path
    return params


def register(mcp, call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]):

    @mcp.tool()
    def list_presentation_slides(path: Optional[str] = None) -> Dict[str, Any]:
        """List all slides in an Impress presentation.

        Returns slide count, names, layout info, and first-shape title.

        Args:
            path: Absolute path to the presentation (optional, uses active doc)
        """
        return call_plugin("list_slides", _p({}, path))

    @mcp.tool()
    def read_presentation_slide(slide_index: int,
                                path: Optional[str] = None) -> Dict[str, Any]:
        """Get all text from a presentation slide and its notes page.

        Args:
            slide_index: Zero-based slide index
            path: Absolute path to the presentation (optional, uses active doc)
        """
        return call_plugin("read_slide_text", _p({
            "slide_index": slide_index}, path))

    @mcp.tool()
    def get_presentation_info(path: Optional[str] = None) -> Dict[str, Any]:
        """Get presentation metadata: slide count, dimensions, master pages.

        Args:
            path: Absolute path to the presentation (optional, uses active doc)
        """
        return call_plugin("get_presentation_info", _p({}, path))

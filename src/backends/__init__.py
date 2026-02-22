"""
Backend factory — returns the right DocumentBackend for the current mode.
"""

import os
from typing import Any, Callable, Dict

from .base import DocumentBackend


def get_backend(call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> DocumentBackend:
    """Return a GuiBackend (default) or HeadlessBackend.

    GUI is the default since the LO plugin is the primary backend.
    Set MCP_LIBREOFFICE_HEADLESS=1 to opt into headless mode.
    """
    headless = os.environ.get("MCP_LIBREOFFICE_HEADLESS", "0") in ("1", "true", "yes")
    if headless:
        from .headless import HeadlessBackend
        return HeadlessBackend()
    else:
        from .gui import GuiBackend
        return GuiBackend(call_plugin)

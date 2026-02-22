"""
Register all MCP tools on the given server instance.
"""

from typing import Any, Callable, Dict

from ..backends.base import DocumentBackend
from . import common_tools, writer_tools, calc_tools, impress_tools


def register_all(mcp, backend: DocumentBackend,
                 call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
    common_tools.register(mcp, backend, call_plugin)
    writer_tools.register(mcp, call_plugin)
    calc_tools.register(mcp, call_plugin)
    impress_tools.register(mcp, call_plugin)

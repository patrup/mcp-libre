"""
HTTP client for the LibreOffice UNO plugin (running inside LO on port 8765).
"""

import os
import time
from typing import Any, Dict, Optional

import httpx

PLUGIN_API_URL = os.environ.get("MCP_PLUGIN_URL", "http://localhost:8765")

_plugin_available: Optional[bool] = None
_plugin_check_time: float = 0.0
_PLUGIN_CHECK_INTERVAL = 30.0


def check_plugin_available() -> bool:
    """Check if the LibreOffice plugin HTTP API is available (cached)."""
    global _plugin_available, _plugin_check_time
    now = time.time()
    if _plugin_available is not None and (now - _plugin_check_time) < _PLUGIN_CHECK_INTERVAL:
        return _plugin_available
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{PLUGIN_API_URL}/health")
            _plugin_available = resp.status_code == 200
    except Exception:
        _plugin_available = False
    _plugin_check_time = now
    return _plugin_available


def call_plugin(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call a tool on the LibreOffice plugin HTTP API."""
    if not check_plugin_available():
        raise RuntimeError(
            "LibreOffice plugin not available. Start LibreOffice with the "
            "MCP extension (HTTP API on http://localhost:8765)."
        )
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{PLUGIN_API_URL}/tools/{tool_name}", json=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        global _plugin_available
        _plugin_available = None
        raise RuntimeError("Lost connection to LibreOffice plugin.")
    except httpx.TimeoutException:
        raise RuntimeError("Plugin API call timed out.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Plugin API error ({e.response.status_code}): "
                           f"{e.response.text}")

"""
LibreOffice MCP Extension - AI Interface Module

This module provides HTTP API interface for external AI assistants to communicate
with the LibreOffice MCP server.
"""

import json
import logging
import os
import threading
from typing import Dict, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .mcp_server import get_mcp_server
from .main_thread_executor import execute_on_main_thread


def _get_version() -> str:
    try:
        from .version import EXTENSION_VERSION
        return EXTENSION_VERSION
    except Exception:
        return "unknown"


_agent_instructions_cache: Optional[str] = None


def _load_agent_instructions() -> str:
    """Load AGENT.md from the project root (cached after first read)."""
    global _agent_instructions_cache
    if _agent_instructions_cache is not None:
        return _agent_instructions_cache
    # pythonpath/ is one level below the extension root
    ext_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for candidate in (
        os.path.join(ext_dir, "AGENT.md"),           # dev-deploy layout
        os.path.join(ext_dir, "..", "AGENT.md"),      # repo root fallback
    ):
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                _agent_instructions_cache = f.read()
            return _agent_instructions_cache
    _agent_instructions_cache = ""
    return _agent_instructions_cache


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP API"""

    # Set at class level by AIInterface before server starts
    mcp_server = None
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            if path == '/':
                self._send_response(200, self._get_server_info())
            elif path == '/tools':
                self._send_response(200, self._get_tools_list())
            elif path == '/health':
                self._send_response(200, {
                    "status": "healthy",
                    "server": "LibreOffice MCP Extension",
                    "version": _get_version(),
                })
            else:
                self._send_response(404, {"error": "Not found"})
                
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self._send_response(500, {"error": str(e)})
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    self._send_response(400, {"error": "Invalid JSON"})
                    return
            else:
                data = {}
            
            if path.startswith('/tools/'):
                # Extract tool name from path
                tool_name = path[7:]  # Remove '/tools/' prefix
                self._handle_tool_execution(tool_name, data)
            elif path == '/execute':
                # Execute tool specified in request body
                if 'tool' not in data:
                    self._send_response(400, {"error": "Missing 'tool' parameter"})
                    return
                tool_name = data['tool']
                parameters = data.get('parameters', {})
                self._handle_tool_execution(tool_name, parameters)
            else:
                self._send_response(404, {"error": "Not found"})
                
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self._send_response(500, {"error": str(e)})
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self._send_cors_headers()
        self.end_headers()
    
    def _handle_tool_execution(self, tool_name: str, parameters: Dict[str, Any]):
        """Handle tool execution requests.

        Dispatches the UNO work to the VCL main thread via AsyncCallback
        so that all UNO calls are thread-safe.
        """
        try:
            result = execute_on_main_thread(
                self.mcp_server.execute_tool_sync,
                tool_name, parameters,
                timeout=30.0,
            )
            self._send_response(200, result)

        except TimeoutError:
            logger.error("Tool %s timed out waiting for main thread", tool_name)
            self._send_response(504, {
                "error": f"Tool '{tool_name}' timed out (main thread busy)"})

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            self._send_response(500, {"error": str(e)})
    
    def _get_server_info(self) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": "LibreOffice MCP Extension",
            "version": _get_version(),
            "description": "MCP server integrated into LibreOffice",
            "endpoints": {
                "GET /": "Server information and agent instructions",
                "GET /tools": "List available tools",
                "GET /health": "Health check",
                "POST /tools/{tool_name}": "Execute specific tool",
                "POST /execute": "Execute tool (tool name in body)"
            },
            "tools_count": len(self.mcp_server.tools),
            "instructions": _load_agent_instructions(),
        }
    
    def _get_tools_list(self) -> Dict[str, Any]:
        """Get list of available tools"""
        return {
            "tools": self.mcp_server.get_tool_list(),
            "count": len(self.mcp_server.tools)
        }
    
    def _send_response(self, status_code: int, data: Dict[str, Any]):
        """Send JSON response with CORS headers"""
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = json.dumps(data, indent=2)
        self.wfile.write(response.encode('utf-8'))
    
    def _send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.client_address[0]} - {format % args}")


class AIInterface:
    """Interface for AI assistants to communicate with the LibreOffice MCP server"""
    
    def __init__(self, port: int = 8765, host: str = "localhost"):
        """
        Initialize the AI interface
        
        Args:
            port: Port to listen on
            host: Host to bind to
        """
        self.port = port
        self.host = host
        self.server = None
        self.server_thread = None
        self.running = False
        logger.info(f"AI Interface initialized for {host}:{port}")
    
    def start(self):
        """Start the HTTP server"""
        try:
            if self.running:
                logger.warning("Server is already running")
                return

            # Inject MCP server reference into handler class
            MCPRequestHandler.mcp_server = get_mcp_server()

            # Do NOT set allow_reuse_address on Windows - it allows multiple
            # servers to shadow the same port, causing empty responses.
            self.server = HTTPServer(
                (self.host, self.port), MCPRequestHandler
            )
            self.running = True

            logger.info(f"Started MCP HTTP server on {self.host}:{self.port}")

            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()

            logger.info("MCP HTTP server started successfully")

        except OSError as e:
            logger.error(f"Failed to bind HTTP server to {self.host}:{self.port}: {e}")
            self.running = False
            raise
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the HTTP server"""
        try:
            if not self.running:
                logger.warning("Server is not running")
                return
            
            self.running = False
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                logger.info("MCP HTTP server stopped")
                
        except Exception as e:
            logger.error(f"Error stopping HTTP server: {e}")
    
    def _run_server(self):
        """Run the HTTP server"""
        try:
            logger.info(f"HTTP server listening on {self.host}:{self.port}")
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we're supposed to be running
                logger.error(f"HTTP server error: {e}")
        finally:
            self.running = False
    
    def is_running(self) -> bool:
        """Check if the server is running"""
        return self.running
    
    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}",
            "thread_alive": self.server_thread.is_alive() if self.server_thread else False
        }


# Global instance
ai_interface = None

def get_ai_interface(port: int = 8765, host: str = "localhost") -> AIInterface:
    """Get or create the global AI interface instance"""
    global ai_interface
    if ai_interface is None:
        ai_interface = AIInterface(port, host)
    return ai_interface

def start_ai_interface(port: int = 8765, host: str = "localhost") -> AIInterface:
    """Start the AI interface HTTP server"""
    interface = get_ai_interface(port, host)
    if not interface.is_running():
        interface.start()
    return interface

def stop_ai_interface():
    """Stop the AI interface HTTP server"""
    global ai_interface
    if ai_interface:
        ai_interface.stop()

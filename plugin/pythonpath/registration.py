"""
LibreOffice MCP Extension - Registration Module

This module handles the registration and lifecycle of the LibreOffice MCP extension.
"""

import uno
import unohelper
import logging
import threading
import traceback
from com.sun.star.task import XJobExecutor
from com.sun.star.lang import XServiceInfo

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Implementation name and service name for the extension
IMPLEMENTATION_NAME = "org.mcp.libreoffice.MCPExtension"
SERVICE_NAMES = ("com.sun.star.task.JobExecutor",)


class MCPExtension(unohelper.Base, XJobExecutor, XServiceInfo):
    """Main LibreOffice MCP Extension class"""
    
    def __init__(self, ctx):
        """Initialize the extension"""
        self.ctx = ctx
        self.ai_interface = None
        self.mcp_server = None
        self.started = False
        logger.info("MCP Extension initialized")
    
    # XJobExecutor interface
    def trigger(self, args):
        """
        Called when extension actions are triggered
        
        Args:
            args: Command arguments
        """
        try:
            logger.info(f"Extension triggered with args: {args}")
            
            if args == "start_mcp_server":
                self._start_mcp_server()
            elif args == "stop_mcp_server":
                self._stop_mcp_server()
            elif args == "restart_mcp_server":
                self._restart_mcp_server()
            elif args == "get_status":
                return self._get_status()
            else:
                logger.warning(f"Unknown trigger args: {args}")
                
        except Exception as e:
            logger.error(f"Error in trigger: {e}")
            logger.error(traceback.format_exc())
    
    # XServiceInfo interface
    def getImplementationName(self):
        """Get implementation name"""
        return IMPLEMENTATION_NAME
    
    def supportsService(self, service_name):
        """Check if service is supported"""
        return service_name in SERVICE_NAMES
    
    def getSupportedServiceNames(self):
        """Get supported service names"""
        return SERVICE_NAMES
    
    # Extension lifecycle methods
    def _start_mcp_server(self):
        """Start the MCP server and AI interface"""
        try:
            if self.started:
                logger.warning("MCP server is already started")
                return
            
            # Import modules here to avoid import issues during extension loading
            from .ai_interface import start_ai_interface
            from .mcp_server import get_mcp_server
            
            # Initialize MCP server
            self.mcp_server = get_mcp_server()
            logger.info("MCP server initialized")
            
            # Start AI interface HTTP server
            self.ai_interface = start_ai_interface(port=8765, host="localhost")
            logger.info("AI interface started")
            
            self.started = True
            logger.info("LibreOffice MCP Extension started successfully")
            
            # Show notification to user
            self._show_notification("MCP Extension Started", 
                                  "LibreOffice MCP server is running on http://localhost:8765")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            logger.error(traceback.format_exc())
            self._show_notification("MCP Extension Error", f"Failed to start: {e}")
    
    def _stop_mcp_server(self):
        """Stop the MCP server and AI interface"""
        try:
            if not self.started:
                logger.warning("MCP server is not running")
                return
            
            # Stop AI interface
            if self.ai_interface:
                from .ai_interface import stop_ai_interface
                stop_ai_interface()
                self.ai_interface = None
                logger.info("AI interface stopped")
            
            # Clean up MCP server
            self.mcp_server = None
            self.started = False
            
            logger.info("LibreOffice MCP Extension stopped")
            self._show_notification("MCP Extension Stopped", "MCP server has been stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")
            logger.error(traceback.format_exc())
    
    def _restart_mcp_server(self):
        """Restart the MCP server"""
        logger.info("Restarting MCP server")
        self._stop_mcp_server()
        self._start_mcp_server()
    
    def _get_status(self):
        """Get extension status"""
        status = {
            "started": self.started,
            "mcp_server": self.mcp_server is not None,
            "ai_interface": self.ai_interface is not None
        }
        
        if self.ai_interface:
            status.update(self.ai_interface.get_status())
        
        logger.info(f"Extension status: {status}")
        return status
    
    def _show_notification(self, title: str, message: str):
        """Show a notification to the user"""
        try:
            # Get the frame and show an info box
            desktop = self.ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", self.ctx)
            
            # For now, just log the notification
            # In a full implementation, you would show a proper LibreOffice notification
            logger.info(f"NOTIFICATION - {title}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")


class ExtensionEventListener:
    """Listener for extension lifecycle events"""
    
    def __init__(self):
        self.extension_instance = None
        logger.info("Extension event listener initialized")
    
    def on_extension_load(self, ctx):
        """Called when extension is loaded"""
        try:
            logger.info("Extension loading...")
            self.extension_instance = MCPExtension(ctx)
            
            # Auto-start the MCP server
            threading.Thread(
                target=self.extension_instance._start_mcp_server,
                daemon=True
            ).start()
            
            logger.info("Extension loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading extension: {e}")
            logger.error(traceback.format_exc())
    
    def on_extension_unload(self):
        """Called when extension is unloaded"""
        try:
            logger.info("Extension unloading...")
            
            if self.extension_instance:
                self.extension_instance._stop_mcp_server()
                self.extension_instance = None
            
            logger.info("Extension unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading extension: {e}")
            logger.error(traceback.format_exc())


# Global extension listener
extension_listener = ExtensionEventListener()


# Extension factory functions
def createInstance(ctx):
    """Create extension instance"""
    try:
        logger.info("Creating extension instance")
        extension_listener.on_extension_load(ctx)
        return extension_listener.extension_instance
        
    except Exception as e:
        logger.error(f"Error creating extension instance: {e}")
        logger.error(traceback.format_exc())
        raise


def getSupportedServiceNames():
    """Get supported service names for extension"""
    return SERVICE_NAMES


def getImplementationName():
    """Get implementation name for extension"""
    return IMPLEMENTATION_NAME


# Component registration
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    createInstance,
    IMPLEMENTATION_NAME,
    SERVICE_NAMES
)

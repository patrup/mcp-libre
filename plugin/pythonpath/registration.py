"""
LibreOffice MCP Extension - Registration Module

Implements XDispatchProvider/XDispatch so menu items (Addons.xcu)
actually call our code when the user clicks them.
"""

import uno
import unohelper
import os
import logging
import threading
import traceback
import socket as _socket
import subprocess as _subprocess

from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XServiceInfo, XInitialization
from com.sun.star.task import XJob
from com.sun.star.beans import PropertyValue

# ── File logger (so we can debug even when LO console is hidden) ─────────────

_log_path = os.path.join(os.path.expanduser("~"), "mcp-extension.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_log_path, encoding="utf-8"),
    ],
)
logger = logging.getLogger("mcp-extension")

IMPLEMENTATION_NAME = "org.mcp.libreoffice.MCPExtension"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)

from .version import EXTENSION_VERSION

EXTENSION_NAME = "LibreOffice MCP Server"
EXTENSION_URL = "https://github.com/quazardous/mcp-libre"

logger.info("=== registration.py loaded — %s v%s ===", EXTENSION_NAME, EXTENSION_VERSION)

# ── Extension config ─────────────────────────────────────────────────────────
# Uses LibreOffice native configuration (MCPServerConfig.xcs/xcu)
# with fallback to hardcoded defaults if UNO config is not yet available.

import json as _json
from com.sun.star.beans import PropertyValue as _PropertyValue

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".mcp-libre")
_PID_FILE = os.path.join(_CONFIG_DIR, "server.pid")

_CONFIG_NODE_PATH = "/org.mcp.libreoffice.Settings/Server"

_DEFAULT_CONFIG = {
    "autostart": True,
    "port": 8765,
    "host": "localhost",
}


def _read_lo_config():
    """Read config from LibreOffice native configuration registry."""
    try:
        ctx = uno.getComponentContext()
        smgr = ctx.ServiceManager
        provider = smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", ctx)
        node_arg = _PropertyValue()
        node_arg.Name = "nodepath"
        node_arg.Value = _CONFIG_NODE_PATH
        access = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess", (node_arg,))
        cfg = {
            "autostart": bool(access.getPropertyValue("AutoStart")),
            "port": int(access.getPropertyValue("Port")),
            "host": str(access.getPropertyValue("Host")),
        }
        access.dispose()
        logger.info(f"Config loaded from LO registry: {cfg}")
        return cfg
    except Exception as e:
        logger.warning(f"LO config read failed (using defaults): {e}")
        return None


def _write_lo_config(values):
    """Write config values to LibreOffice native configuration registry.

    Args:
        values: dict with keys like "autostart", "port", "host".
    """
    try:
        ctx = uno.getComponentContext()
        smgr = ctx.ServiceManager
        provider = smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", ctx)
        node_arg = _PropertyValue()
        node_arg.Name = "nodepath"
        node_arg.Value = _CONFIG_NODE_PATH
        update = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationUpdateAccess", (node_arg,))
        # Map our keys to LO property names
        key_map = {"autostart": "AutoStart", "port": "Port", "host": "Host"}
        for key, value in values.items():
            lo_key = key_map.get(key)
            if lo_key:
                update.setPropertyValue(lo_key, value)
        update.commitChanges()
        update.dispose()
        logger.info(f"Config written to LO registry: {values}")
    except Exception as e:
        logger.error(f"LO config write failed: {e}")


def _load_config():
    """Load config: try LO native registry first, then fall back to defaults."""
    cfg = _read_lo_config()
    if cfg is not None:
        return cfg
    return dict(_DEFAULT_CONFIG)


_config = _load_config()
logger.info(f"Config: autostart={_config['autostart']}, port={_config['port']}")

# ── Port / zombie management ─────────────────────────────────────────────────


def _probe_health(host, port, timeout=2):
    """Probe the HTTP health endpoint. Returns True if OUR server responds."""
    try:
        import http.client
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        return "LibreOffice MCP" in body
    except Exception:
        return False


def _is_port_bound(host, port, timeout=1):
    """Check if a port is bound (something is listening)."""
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def _get_pids_on_port(port):
    """Get PIDs of processes listening on a port (Windows)."""
    pids = set()
    try:
        result = _subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(_subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(int(pid))
    except Exception as e:
        logger.warning(f"Failed to enumerate PIDs on port {port}: {e}")
    return pids


def _kill_zombies_on_port(host, port):
    """Kill zombie processes on the port that aren't serving our MCP health."""
    if not _is_port_bound(host, port):
        logger.debug(f"Port {port} is free")
        return True  # Port is free

    if _probe_health(host, port):
        logger.info(f"Port {port} already has a healthy MCP server")
        return False  # Our server is already running, don't kill

    # Port is bound but not our server -> zombie
    pids = _get_pids_on_port(port)
    my_pid = os.getpid()
    for pid in pids:
        if pid == my_pid:
            continue
        logger.warning(f"Killing zombie process PID {pid} on port {port}")
        try:
            _subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=5,
                creationflags=getattr(_subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to kill PID {pid}: {e}")

    # Wait and verify
    import time
    time.sleep(1)
    if _is_port_bound(host, port):
        logger.error(f"Port {port} still bound after killing zombies")
        return False
    logger.info(f"Zombies cleared from port {port}")
    return True


def _write_pid_file():
    """Write current PID to server.pid."""
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _remove_pid_file():
    """Remove server.pid."""
    try:
        if os.path.exists(_PID_FILE):
            os.unlink(_PID_FILE)
    except Exception:
        pass


# ── Shared state (singleton across dispatch calls) ───────────────────────────

_mcp_state = {
    "started": False,
    "mcp_server": None,
    "ai_interface": None,
}

# Cross-load guard: prevent two module loads from both auto-starting

# ── Server state & dynamic menu icons ─────────────────────────────────────

_STATE_STOPPED = "stopped"
_STATE_STARTING = "starting"
_STATE_RUNNING = "running"
_server_state = _STATE_STOPPED

_status_listeners_lock = threading.Lock()
_status_listeners_list = []  # [(listener, parsed_url), ...]


def _get_menu_text(url_path):
    """Return dynamic menu-item text based on current server state."""
    if url_path == "toggle_mcp_server":
        if _server_state == _STATE_RUNNING:
            return "Stop Server"
        if _server_state == _STATE_STARTING:
            return "Starting\u2026"
        return "Start Server"
    return None


def _icon_name_for_state():
    """Return the icon filename prefix for the current server state."""
    if _server_state == _STATE_RUNNING:
        return "running"
    if _server_state == _STATE_STARTING:
        return "starting"
    return "stopped"


def _get_extension_url():
    """Get the base URL of the installed extension package."""
    try:
        ctx = uno.getComponentContext()
        pip = ctx.getByName(
            "/singletons/com.sun.star.deployment.PackageInformationProvider")
        return pip.getPackageLocation("org.mcp.libreoffice.extension")
    except Exception:
        return None


def _load_icon_graphic(icon_filename):
    """Load a PNG icon from the extension as XGraphic."""
    try:
        ext_url = _get_extension_url()
        logger.debug(f"Extension URL: {ext_url}")
        if not ext_url:
            logger.warning("Extension URL is None — icons won't load")
            return None
        ctx = uno.getComponentContext()
        smgr = ctx.ServiceManager
        gp = smgr.createInstanceWithContext(
            "com.sun.star.graphic.GraphicProvider", ctx)
        pv = PropertyValue()
        pv.Name = "URL"
        icon_url = ext_url + "/icons/" + icon_filename
        pv.Value = icon_url
        logger.debug(f"Loading icon: {icon_url}")
        result = gp.queryGraphic((pv,))
        logger.debug(f"Icon loaded: {result is not None}")
        return result
    except Exception as e:
        logger.debug(f"Failed to load icon {icon_filename}: {e}")
        return None


# Command URLs that get dynamic icons
_ICON_CMDS = (
    "org.mcp.libreoffice:toggle_mcp_server",
    "org.mcp.libreoffice:get_status",
)

_MODULE_IDS = (
    "com.sun.star.text.TextDocument",
    "com.sun.star.sheet.SpreadsheetDocument",
    "com.sun.star.presentation.PresentationDocument",
    "com.sun.star.drawing.DrawingDocument",
)


def _update_menu_icons():
    """Push the current-state icon into every module's ImageManager."""
    return  # DISABLED: suspected cause of black menu rendering
    try:
        prefix = _icon_name_for_state()
        graphic = _load_icon_graphic(f"{prefix}_16.png")
        if graphic is None:
            logger.warning("Icon graphic is None for %s", prefix)
            return

        ctx = uno.getComponentContext()
        smgr = ctx.ServiceManager
        supplier = smgr.createInstanceWithContext(
            "com.sun.star.ui.ModuleUIConfigurationManagerSupplier", ctx)

        ok_count = 0
        for mod_id in _MODULE_IDS:
            try:
                cfg_mgr = supplier.getUIConfigurationManager(mod_id)
                img_mgr = cfg_mgr.getImageManager()
                for cmd in _ICON_CMDS:
                    try:
                        if img_mgr.hasImage(0, cmd):
                            img_mgr.replaceImages(0, (cmd,), (graphic,))
                        else:
                            img_mgr.insertImages(0, (cmd,), (graphic,))
                        ok_count += 1
                    except Exception as e:
                        logger.info("ImageManager %s cmd %s: %s", mod_id, cmd, e)
            except Exception as e:
                logger.info("ImageManager skip %s: %s", mod_id, e)
        logger.info("Menu icons updated -> %s (%d insertions)", prefix, ok_count)
    except Exception as e:
        logger.warning("Dynamic icon update failed: %s", e)


def _fire_status_event(listener, url, text):
    """Send a FeatureStateEvent to one listener."""
    ev = uno.createUnoStruct("com.sun.star.frame.FeatureStateEvent")
    ev.FeatureURL = url
    ev.IsEnabled = True
    ev.Requery = False
    if text is not None:
        ev.State = text
    listener.statusChanged(ev)


def _set_server_state(new_state):
    """Update global server state and push it to every registered listener."""
    global _server_state
    _server_state = new_state
    logger.info(f"Server state -> {new_state}")
    _notify_all_listeners()
    # Update graphical icons in a thread (avoids blocking UI)
    threading.Thread(target=_update_menu_icons, daemon=True).start()


def _notify_all_listeners():
    """Push the current state to every registered status listener."""
    with _status_listeners_lock:
        alive = []
        for listener, url in _status_listeners_list:
            text = _get_menu_text(url.Path)
            try:
                _fire_status_event(listener, url, text)
                alive.append((listener, url))
            except Exception as e:
                logger.debug(f"Dropping dead status listener: {e}")
        _status_listeners_list[:] = alive


def _start_mcp_server():
    """Start the MCP HTTP server (called in a background thread)."""
    if _mcp_state["started"]:
        logger.warning("MCP server is already running (in-memory state)")
        _set_server_state(_STATE_RUNNING)
        return

    port = _config.get("port", 8765)
    host = _config.get("host", "localhost")

    # Check if our server is already running (e.g. from another module load)
    if _probe_health(host, port):
        logger.info("MCP server already healthy on port, marking as started")
        _mcp_state["started"] = True
        _set_server_state(_STATE_RUNNING)
        return

    _set_server_state(_STATE_STARTING)

    # Kill zombies on the port
    port_free = _kill_zombies_on_port(host, port)
    if not port_free:
        _set_server_state(_STATE_STOPPED)
        raise RuntimeError(f"Cannot free port {port}")

    try:
        from ai_interface import start_ai_interface
        from mcp_server import get_mcp_server

        _mcp_state["mcp_server"] = get_mcp_server()
        _mcp_state["ai_interface"] = start_ai_interface(port=port, host=host)
        _mcp_state["started"] = True
        _write_pid_file()
        _set_server_state(_STATE_RUNNING)
        logger.info(f"MCP Extension started -- http://{host}:{port}")
    except Exception as e:
        _set_server_state(_STATE_STOPPED)
        logger.error(f"Failed to start MCP server: {e}")
        logger.error(traceback.format_exc())
        raise


def _stop_mcp_server():
    """Stop the MCP HTTP server."""
    if not _mcp_state["started"]:
        logger.warning("MCP server is not running")
        _set_server_state(_STATE_STOPPED)
        return
    try:
        from ai_interface import stop_ai_interface
        stop_ai_interface()
    except Exception:
        pass
    _mcp_state["ai_interface"] = None
    _mcp_state["mcp_server"] = None
    _mcp_state["started"] = False
    _remove_pid_file()
    _set_server_state(_STATE_STOPPED)
    logger.info("MCP Extension stopped")


# ── Message box helper ───────────────────────────────────────────────────────

def _msgbox(ctx, title, message):
    """Show an info message box in LibreOffice."""
    try:
        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        frame = desktop.getCurrentFrame()
        if frame is None:
            logger.info(f"MSGBOX (no frame) - {title}: {message}")
            return
        window = frame.getContainerWindow()
        toolkit = smgr.createInstanceWithContext(
            "com.sun.star.awt.Toolkit", ctx)
        box = toolkit.createMessageBox(
            window, 1, 1, title, message)  # INFOBOX, OK button
        box.execute()
    except Exception as e:
        logger.info(f"MSGBOX fallback - {title}: {message} (error: {e})")


# ── Protocol handler (dispatches menu clicks) ────────────────────────────────

class MCPExtension(unohelper.Base, XDispatch, XDispatchProvider,
                   XServiceInfo, XInitialization):
    """Protocol handler that dispatches menu actions."""

    def __init__(self, ctx):
        unohelper.Base.__init__(self)
        self.ctx = ctx
        self._frame = None
        logger.debug("MCPExtension.__init__ called")

    # -- XInitialization ------------------------------------------------------
    def initialize(self, args):
        try:
            if args:
                self._frame = args[0]
            logger.debug(f"MCPExtension.initialize called, frame={self._frame}")
            # Pre-load icons into ImageManager so first menu display has them
            threading.Thread(target=_update_menu_icons, daemon=True).start()
        except Exception as e:
            logger.error(f"initialize error: {e}")
            logger.error(traceback.format_exc())

    # -- XDispatchProvider ----------------------------------------------------
    def queryDispatch(self, url, target_frame_name, search_flags):
        try:
            logger.debug(f"queryDispatch: Complete={url.Complete} "
                         f"Protocol={url.Protocol} Path={url.Path}")
            if url.Protocol == "org.mcp.libreoffice:":
                return self
        except Exception as e:
            logger.error(f"queryDispatch error: {e}")
            logger.error(traceback.format_exc())
        return None

    def queryDispatches(self, requests):
        return [self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags)
                for r in requests]

    # -- XDispatch ------------------------------------------------------------
    def dispatch(self, url, args):
        """Called when the user clicks a menu item."""
        try:
            complete = url.Complete
            logger.info(f"dispatch called: {complete}")

            # URL format: org.mcp.libreoffice:<command>
            cmd = url.Path

            logger.info(f"command: {cmd}")

            if cmd == "start_mcp_server":
                _set_server_state(_STATE_STARTING)
                threading.Thread(target=self._do_start, daemon=True).start()
            elif cmd == "stop_mcp_server":
                self._do_stop()
            elif cmd == "restart_mcp_server":
                self._do_restart()
            elif cmd == "toggle_mcp_server":
                if _mcp_state["started"]:
                    self._do_stop()
                else:
                    _set_server_state(_STATE_STARTING)
                    threading.Thread(target=self._do_start, daemon=True).start()
            elif cmd == "get_status":
                self._do_status()
            elif cmd == "about":
                self._do_about()
            else:
                logger.warning(f"Unknown command: {cmd}")
                _msgbox(self.ctx, "MCP Extension",
                        f"Unknown command: {cmd}\nURL: {complete}")
        except Exception as e:
            logger.error(f"Error in dispatch: {e}")
            logger.error(traceback.format_exc())
            _msgbox(self.ctx, "MCP Error", str(e))

    def addStatusListener(self, listener, url):
        with _status_listeners_lock:
            _status_listeners_list.append((listener, url))
        # Send current state immediately so the menu renders correctly
        text = _get_menu_text(url.Path)
        if text is not None:
            try:
                _fire_status_event(listener, url, text)
            except Exception as e:
                logger.debug(f"Initial status event failed: {e}")

    def removeStatusListener(self, listener, url):
        with _status_listeners_lock:
            _status_listeners_list[:] = [
                (l, u) for l, u in _status_listeners_list
                if not (l is listener and u.Complete == url.Complete)
            ]

    # -- Actions --------------------------------------------------------------

    def _do_start(self):
        try:
            _start_mcp_server()
            host = _config.get("host", "localhost")
            port = _config.get("port", 8765)
            _msgbox(self.ctx, "MCP Server",
                    f"MCP server started.\nhttp://{host}:{port}")
        except Exception as e:
            _msgbox(self.ctx, "MCP Error", f"Failed to start:\n{e}")

    def _do_stop(self):
        _stop_mcp_server()
        _msgbox(self.ctx, "MCP Server", "MCP server stopped.")

    def _do_restart(self):
        """Stop, kill zombies, and restart."""
        _stop_mcp_server()
        port = _config.get("port", 8765)
        host = _config.get("host", "localhost")
        _kill_zombies_on_port(host, port)
        _set_server_state(_STATE_STARTING)
        threading.Thread(target=self._do_start, daemon=True).start()

    def _do_status(self):
        port = _config.get("port", 8765)
        host = _config.get("host", "localhost")
        mem_state = _mcp_state["started"]

        # Build instant status from in-memory state
        initial_status = "STARTED" if mem_state else "STOPPED"
        initial_lines = [
            f"MCP Server: {initial_status}",
            f"Version: {EXTENSION_VERSION}",
            f"Port: {port}  Host: {host}",
            f"Autostart: {_config.get('autostart', True)}",
            "",
            "Health check: probing...",
        ]

        # Create a UNO dialog so we can update it live
        try:
            ctx = self.ctx
            smgr = ctx.ServiceManager

            dlg_model = smgr.createInstanceWithContext(
                "com.sun.star.awt.UnoControlDialogModel", ctx)
            dlg_model.Title = "MCP Server Status"
            dlg_model.Width = 230
            dlg_model.Height = 110

            lbl = dlg_model.createInstance(
                "com.sun.star.awt.UnoControlFixedTextModel")
            lbl.Name = "StatusText"
            lbl.PositionX = 10
            lbl.PositionY = 6
            lbl.Width = 210
            lbl.Height = 72
            lbl.MultiLine = True
            lbl.Label = "\n".join(initial_lines)
            dlg_model.insertByName("StatusText", lbl)

            btn = dlg_model.createInstance(
                "com.sun.star.awt.UnoControlButtonModel")
            btn.Name = "OKBtn"
            btn.PositionX = 90
            btn.PositionY = 88
            btn.Width = 50
            btn.Height = 14
            btn.Label = "OK"
            btn.PushButtonType = 1  # OK
            dlg_model.insertByName("OKBtn", btn)

            dlg = smgr.createInstanceWithContext(
                "com.sun.star.awt.UnoControlDialog", ctx)
            dlg.setModel(dlg_model)
            toolkit = smgr.createInstanceWithContext(
                "com.sun.star.awt.Toolkit", ctx)
            dlg.createPeer(toolkit, None)

            # Background probe updates the label while dialog is open
            def probe_and_update():
                try:
                    import time
                    time.sleep(0.05)
                    http_ok = _probe_health(host, port, timeout=1)
                    if mem_state:
                        health = "OK" if http_ok else "FAIL (not responding)"
                    else:
                        if _is_port_bound(host, port, timeout=0.5):
                            health = "ZOMBIE (port bound, server stopped)"
                        else:
                            health = "-- (server stopped)"
                    lines = [
                        f"MCP Server: {initial_status}",
                        f"Version: {EXTENSION_VERSION}",
                        f"Port: {port}  Host: {host}",
                        f"Autostart: {_config.get('autostart', True)}",
                        "",
                        f"Health check: {health}",
                    ]
                    if mem_state and http_ok:
                        lines.append(f"URL: http://{host}:{port}/health")
                    try:
                        dlg_model.getByName("StatusText").Label = "\n".join(lines)
                    except Exception:
                        pass  # dialog already closed
                except Exception as e:
                    logger.debug(f"Status probe error: {e}")

            threading.Thread(target=probe_and_update, daemon=True).start()
            dlg.execute()
            dlg.dispose()
        except Exception as e:
            logger.error(f"Status dialog error: {e}")
            # Fallback to simple msgbox
            _msgbox(self.ctx, "MCP Server Status",
                    f"Status: {initial_status}\nVersion: {EXTENSION_VERSION}")

    def _do_about(self):
        lines = [
            f"{EXTENSION_NAME}",
            f"Version: {EXTENSION_VERSION}",
            f"",
            f"MCP (Model Context Protocol) server extension",
            f"for LibreOffice document manipulation via AI.",
            f"",
            f"GitHub: {EXTENSION_URL}",
        ]
        _msgbox(self.ctx, "About MCP Extension", "\n".join(lines))

    # -- XServiceInfo ---------------------------------------------------------
    def getImplementationName(self):
        return IMPLEMENTATION_NAME

    def supportsService(self, name):
        return name in SERVICE_NAMES

    def getSupportedServiceNames(self):
        return SERVICE_NAMES


# ── Options dialog handler (Tools > Options > MCP Server) ────────────────────

from com.sun.star.awt import XContainerWindowEventHandler


class MCPOptionsHandler(unohelper.Base, XContainerWindowEventHandler,
                        XServiceInfo):
    """Event handler for the MCP Server options page in Tools > Options."""

    _IMPL_NAME = "org.mcp.libreoffice.MCPOptionsHandler"
    _SVC_NAMES = ("org.mcp.libreoffice.MCPOptionsHandler",)

    def __init__(self, ctx):
        unohelper.Base.__init__(self)
        self.ctx = ctx
        logger.debug("MCPOptionsHandler.__init__")

    # -- XContainerWindowEventHandler -----------------------------------------

    def callHandlerMethod(self, xWindow, eventObject, methodName):
        logger.debug(f"Options handler: {methodName} / {eventObject}")
        if methodName != "external_event":
            return False

        if eventObject == "initialize":
            self._load_to_dialog(xWindow)
            return True
        elif eventObject == "ok":
            self._save_from_dialog(xWindow)
            return True
        elif eventObject == "back":
            self._load_to_dialog(xWindow)
            return True
        return False

    def getSupportedMethodNames(self):
        return ("external_event",)

    # -- Load / Save ----------------------------------------------------------

    def _load_to_dialog(self, xWindow):
        try:
            cfg = _read_lo_config()
            if cfg is None:
                cfg = dict(_DEFAULT_CONFIG)
            logger.debug(f"Options: loading {cfg}")

            xWindow.getControl("AutoStartCheck").setState(
                1 if cfg["autostart"] else 0)
            xWindow.getControl("HostField").setText(cfg["host"])
            xWindow.getControl("PortField").setValue(float(cfg["port"]))
            xWindow.getControl("UrlText").setText(
                f"Health check: http://{cfg['host']}:{cfg['port']}/health")
        except Exception as e:
            logger.error(f"Options load error: {e}")
            logger.error(traceback.format_exc())

    def _save_from_dialog(self, xWindow):
        try:
            new_values = {
                "autostart": xWindow.getControl("AutoStartCheck").getState() == 1,
                "port": int(xWindow.getControl("PortField").getValue()),
                "host": xWindow.getControl("HostField").getText(),
            }
            logger.info(f"Options: saving {new_values}")

            # Detect if server needs restart (port or host changed)
            old_port = _config.get("port", 8765)
            old_host = _config.get("host", "localhost")
            needs_restart = (
                _mcp_state["started"]
                and (new_values["port"] != old_port
                     or new_values["host"] != old_host)
            )

            _write_lo_config(new_values)
            _config.update(new_values)

            if needs_restart:
                logger.info(f"Options: port/host changed "
                            f"({old_host}:{old_port} -> "
                            f"{new_values['host']}:{new_values['port']}), "
                            f"restarting server...")
                _stop_mcp_server()
                _kill_zombies_on_port(old_host, old_port)
                threading.Thread(
                    target=self._restart_after_config_change,
                    daemon=True).start()

        except Exception as e:
            logger.error(f"Options save error: {e}")
            logger.error(traceback.format_exc())

    def _restart_after_config_change(self):
        """Restart server on new port after config change."""
        try:
            import time
            time.sleep(1)  # Let old socket close
            _start_mcp_server()
            logger.info("Server restarted on new config")
        except Exception as e:
            logger.error(f"Restart after config change failed: {e}")

    # -- XServiceInfo ---------------------------------------------------------

    def getImplementationName(self):
        return self._IMPL_NAME

    def supportsService(self, name):
        return name in self._SVC_NAMES

    def getSupportedServiceNames(self):
        return self._SVC_NAMES


# ── AutoStart Job (fires on onFirstVisibleTask) ─────────────────────────────

class MCPAutoStartJob(unohelper.Base, XJob, XServiceInfo):
    """LO Job triggered by onFirstVisibleTask — starts MCP server at LO launch."""
    _IMPL_NAME = "org.mcp.libreoffice.MCPAutoStart"
    _SVC_NAMES = ("com.sun.star.task.Job",)

    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        logger.info("AutoStart job triggered (onFirstVisibleTask)")
        try:
            if _config.get("autostart", True):
                threading.Thread(
                    target=_start_mcp_server, daemon=True,
                    name="mcp-job-start").start()
            else:
                logger.info("AutoStart job: autostart disabled in config")
        except Exception as e:
            logger.error(f"AutoStart job failed: {e}")
        return ()

    def getImplementationName(self):
        return self._IMPL_NAME

    def supportsService(self, name):
        return name in self._SVC_NAMES

    def getSupportedServiceNames(self):
        return self._SVC_NAMES


# ── UNO component registration ──────────────────────────────────────────────

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    MCPExtension,
    IMPLEMENTATION_NAME,
    SERVICE_NAMES,
)
g_ImplementationHelper.addImplementation(
    MCPOptionsHandler,
    MCPOptionsHandler._IMPL_NAME,
    MCPOptionsHandler._SVC_NAMES,
)
g_ImplementationHelper.addImplementation(
    MCPAutoStartJob,
    MCPAutoStartJob._IMPL_NAME,
    MCPAutoStartJob._SVC_NAMES,
)

logger.info("g_ImplementationHelper configured (3 services)")

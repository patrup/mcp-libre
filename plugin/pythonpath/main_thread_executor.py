"""
MainThreadExecutor — dispatch UNO calls to the VCL main thread.

The MCP HTTP server runs in a daemon thread.  UNO is *not* thread-safe:
calling it from a background thread causes black menus, crashes on large
docs, and random corruption.

Solution: use com.sun.star.awt.AsyncCallback.addCallback() to post work
into the VCL event loop.  The HTTP thread blocks on a threading.Event
until the main thread has executed the work item and stored the result.

Fallback: if AsyncCallback is unavailable (unit-test, headless without
a toolkit, …), the function is called directly with a warning.
"""

import logging
import queue
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Work item
# ---------------------------------------------------------------------------

class _WorkItem:
    __slots__ = ("fn", "args", "kwargs", "event", "result", "exception")

    def __init__(self, fn: Callable, args: tuple, kwargs: dict):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.event = threading.Event()
        self.result = None
        self.exception = None


# ---------------------------------------------------------------------------
# Global queue drained by the VCL callback
# ---------------------------------------------------------------------------

_work_queue: queue.Queue = queue.Queue()


# ---------------------------------------------------------------------------
# XCallback implementation
# ---------------------------------------------------------------------------

_async_callback_service = None   # cached UNO service
_init_lock = threading.Lock()
_initialized = False


def _get_async_callback():
    """Lazily create the AsyncCallback UNO service and XCallback instance."""
    global _async_callback_service, _callback_instance, _initialized
    if _initialized:
        return _async_callback_service
    with _init_lock:
        if _initialized:
            return _async_callback_service
        try:
            import uno
            ctx = uno.getComponentContext()
            smgr = ctx.ServiceManager
            _async_callback_service = smgr.createInstanceWithContext(
                "com.sun.star.awt.AsyncCallback", ctx)
            if _async_callback_service is None:
                raise RuntimeError("createInstance returned None")
            _callback_instance = _make_callback_instance()
            logger.info("MainThreadExecutor initialized (AsyncCallback ready)")
        except Exception as exc:
            logger.warning(
                "AsyncCallback unavailable (%s) — UNO calls will run "
                "in the HTTP thread (legacy behaviour)", exc)
            _async_callback_service = None
        _initialized = True
        return _async_callback_service


def _make_callback_instance():
    """Create a proper UNO XCallback object (requires unohelper at runtime)."""
    import unohelper
    from com.sun.star.awt import XCallback

    class _MainThreadCallback(unohelper.Base, XCallback):
        """XCallback implementation that drains the work queue on notify()."""

        def notify(self, _ignored):
            """Called by VCL on the main thread."""
            while True:
                try:
                    item = _work_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    item.result = item.fn(*item.args, **item.kwargs)
                except Exception as exc:
                    item.exception = exc
                finally:
                    item.event.set()

    return _MainThreadCallback()


# Singleton created lazily (needs UNO runtime available).
_callback_instance = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_on_main_thread(fn: Callable, *args,
                           timeout: float = 30.0,
                           **kwargs) -> Any:
    """
    Execute *fn(*args, **kwargs)* on the LibreOffice main (VCL) thread
    and return the result.  Blocks the calling thread up to *timeout* seconds.

    Raises TimeoutError if the main thread doesn't process the item in time.
    Re-raises any exception thrown by *fn*.
    """
    svc = _get_async_callback()

    if svc is None:
        # Fallback: call directly (old behaviour, not thread-safe).
        return fn(*args, **kwargs)

    item = _WorkItem(fn, args, kwargs)
    _work_queue.put(item)

    # Poke the VCL event loop so it calls our notify().
    try:
        import uno
        svc.addCallback(_callback_instance, uno.Any("void", None))
    except Exception:
        # If addCallback itself fails, still try with a plain None
        svc.addCallback(_callback_instance, None)

    if not item.event.wait(timeout):
        raise TimeoutError(
            f"Main-thread execution of {fn.__name__} timed out "
            f"after {timeout}s")

    if item.exception is not None:
        raise item.exception

    return item.result

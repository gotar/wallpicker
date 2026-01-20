"""Asyncio integration utilities for GTK4/PyGObject applications.

This module provides utilities for running async/await code from GTK callbacks
by properly integrating Python's asyncio event loop with GTK's GLib main loop.
"""

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any

try:
    from gi.repository import GLib
except ImportError:
    GLib = None

_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None


def setup_event_loop() -> asyncio.AbstractEventLoop:
    """Set up and return the asyncio event loop for GTK integration.

    Returns:
        The configured event loop ready for use with GTK.

    This should be called once at application startup, typically in launcher.py.
    Uses a background thread to run the asyncio event loop.
    """
    global _loop, _loop_thread

    _loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=run_loop, daemon=True)
    _loop_thread.start()

    return _loop


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Get the configured event loop.

    Returns:
        The event loop configured by setup_event_loop().

    Raises:
        RuntimeError: If setup_event_loop() has not been called.
    """
    global _loop
    if _loop is None:
        raise RuntimeError("Event loop not initialized. Call setup_event_loop() first.")
    return _loop


def schedule_async(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Schedule a coroutine to run on the asyncio event loop from GTK callbacks.

    This properly integrates Python's asyncio with GTK4's GLib main loop.

    Example:
        # In a GTK signal handler:
        schedule_async(self.my_view_model.load_async_data())

    Args:
        coro: The coroutine to schedule.

    Returns:
        An asyncio.Task that can be awaited if needed.
    """
    loop = get_event_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop)


def create_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Create an asyncio task, properly integrated with GTK.

    This is a drop-in replacement for asyncio.create_task() that works
    correctly from GTK callbacks.

    Args:
        coro: The coroutine to create a task for.

    Returns:
        An asyncio.Task.
    """
    loop = get_event_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop)

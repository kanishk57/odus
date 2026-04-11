"""
Global Hotkey Listener — triggers screen capture from any application.

DEV 1 owns this module.

Default hotkey: Ctrl+Shift+O (configurable via ODUS_HOTKEY env var).
Uses pynput for X11; evdev fallback is a stretch goal for Wayland.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Callable

from pynput import keyboard

from odus.events import EventType, OdusEvent, get_event_bus

logger = logging.getLogger(__name__)

# Default hotkey combo
DEFAULT_HOTKEY = "<ctrl>+<shift>+o"


def _parse_hotkey(hotkey_str: str) -> str:
    """
    Convert a user-friendly hotkey string to pynput format.
    e.g. 'ctrl+shift+o' → '<ctrl>+<shift>+o'
    """
    parts = hotkey_str.lower().split("+")
    formatted = []
    for part in parts:
        part = part.strip()
        if part in ("ctrl", "shift", "alt", "cmd", "super"):
            formatted.append(f"<{part}>")
        else:
            formatted.append(part)
    return "+".join(formatted)


class HotkeyListener:
    """
    Listens for a global hotkey and emits CAPTURE_STARTED on the event bus.

    Usage:
        listener = HotkeyListener(on_trigger=my_capture_callback)
        listener.start()   # non-blocking, runs in background thread
        ...
        listener.stop()
    """

    def __init__(self, on_trigger: Callable[[], None] | None = None) -> None:
        hotkey_env = os.environ.get("ODUS_HOTKEY", "")
        if hotkey_env:
            self._hotkey_str = _parse_hotkey(hotkey_env)
        else:
            self._hotkey_str = DEFAULT_HOTKEY

        self._on_trigger = on_trigger
        self._listener: keyboard.GlobalHotKeys | None = None
        self._bus = get_event_bus()

        logger.info("HotkeyListener configured | hotkey=%s", self._hotkey_str)

    def _on_activate(self) -> None:
        """Called when the hotkey is pressed."""
        logger.info("🔥 Hotkey activated!")

        # Emit event (fire-and-forget from sync context)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED))
            )
        except RuntimeError:
            # No running loop — we're in a background thread
            # The callback approach handles this case
            pass

        if self._on_trigger:
            self._on_trigger()

    def start(self) -> None:
        """Start listening for the hotkey (non-blocking background thread)."""
        self._listener = keyboard.GlobalHotKeys(
            {self._hotkey_str: self._on_activate}
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("HotkeyListener started — press %s to capture", self._hotkey_str)

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("HotkeyListener stopped")

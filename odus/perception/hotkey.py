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
from typing import Callable, Awaitable

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


class EvdevHotkeyListener:
    """Fallback hotkey listener using evdev (works on Wayland)."""

    def __init__(self, hotkey_str: str, on_trigger_async: Callable[[], Awaitable[None]] | None):
        self._hotkey_str = hotkey_str
        self._on_trigger_async = on_trigger_async
        self._device = self._find_keyboard()
        self._task = None
        self._parse_evdev_hotkey(hotkey_str)

    def _parse_evdev_hotkey(self, hotkey_str: str):
        try:
            from evdev import ecodes
        except ImportError:
            return

        hotkey_lower = hotkey_str.lower()
        self._req_ctrl = '<ctrl>' in hotkey_lower
        self._req_shift = '<shift>' in hotkey_lower
        self._req_alt = '<alt>' in hotkey_lower
        self._req_super = '<super>' in hotkey_lower or '<cmd>' in hotkey_lower
        
        # extract the main key
        parts = [p for p in hotkey_lower.split('+') if not p.startswith('<')]
        main_key = parts[0] if parts else 'o'
        
        # map main key to evdev ecode
        key_name = f"KEY_{main_key.upper()}"
        self._main_keycode = getattr(ecodes, key_name, ecodes.KEY_O)

    def _find_keyboard(self):
        try:
            import evdev
            for path in evdev.list_devices():
                dev = evdev.InputDevice(path)
                caps = dev.capabilities(verbose=True)
                if ('EV_KEY', 1) in caps:
                    return dev
            raise RuntimeError("No keyboard found")
        except ImportError:
            raise RuntimeError("evdev is not installed")
        except PermissionError:
            raise RuntimeError("Permission denied to access /dev/input. Please run: sudo usermod -aG input $USER")

    async def listen(self):
        import evdev
        from evdev import ecodes
        
        ctrl_pressed = False
        shift_pressed = False
        alt_pressed = False
        super_pressed = False
        
        try:
            async for event in self._device.async_read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = evdev.categorize(event)
                    
                    # Track modifier states
                    if key_event.scancode in [ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL]:
                        ctrl_pressed = (key_event.keystate != key_event.key_up)
                    if key_event.scancode in [ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT]:
                        shift_pressed = (key_event.keystate != key_event.key_up)
                    if key_event.scancode in [ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT]:
                        alt_pressed = (key_event.keystate != key_event.key_up)
                    if key_event.scancode in [ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA]:
                        super_pressed = (key_event.keystate != key_event.key_up)
                    
                    # Detect main key press
                    if key_event.scancode == self._main_keycode and key_event.keystate == key_event.key_down:
                        if (
                            (not self._req_ctrl or ctrl_pressed) and 
                            (not self._req_shift or shift_pressed) and
                            (not self._req_alt or alt_pressed) and
                            (not self._req_super or super_pressed)
                        ):
                            if self._on_trigger_async:
                                await self._on_trigger_async()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Evdev loop error: %s", e)

    def start(self):
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self.listen())
            logger.info("EvdevHotkeyListener started")
        except RuntimeError as e:
            logger.error("EvdevHotkeyListener requires a running event loop")
            raise e

    def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
            
        if getattr(self, '_device', None):
            try:
                self._device.close()
            except Exception as e:
                logger.error("Error closing evdev device: %s", e)
            self._device = None
            
        logger.info("EvdevHotkeyListener stopped")


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
        self._listener = None
        self._bus = get_event_bus()
        
        # Capture the main asyncio loop so background pynput threads can emit safely
        try:
            self._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._main_loop = asyncio.get_event_loop()

        self._session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        logger.info("HotkeyListener configured | session=%s | hotkey=%s", self._session_type, self._hotkey_str)

    def _on_activate(self) -> None:
        """Called when the hotkey is pressed (pynput path)."""
        logger.info("🔥 Hotkey activated!")

        # Push to the main asyncio loop safely from the thread
        if self._main_loop and self._main_loop.is_running():
            async def _emit_event():
                await self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED))
            asyncio.run_coroutine_threadsafe(_emit_event(), self._main_loop)

        if self._on_trigger:
            self._on_trigger()

    async def _async_on_activate(self) -> None:
        """Called when the hotkey is pressed via evdev on Wayland."""
        logger.info("🔥 Hotkey activated (Wayland)!")
        await self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED))
        if self._on_trigger:
            self._on_trigger()

    def start(self) -> None:
        """Start listening for the hotkey."""
        if self._session_type == "wayland":
            logger.info("Wayland detected — attempting to use EvdevHotkeyListener")
            try:
                self._listener = EvdevHotkeyListener(
                    hotkey_str=self._hotkey_str,
                    on_trigger_async=self._async_on_activate
                )
                self._listener.start()
                return
            except Exception as e:
                logger.warning("EvdevHotkeyListener failed to start: %s. Falling back to pynput.", e)

        self._listener = keyboard.GlobalHotKeys(
            {self._hotkey_str: self._on_activate}
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("HotkeyListener (pynput) started — press %s to capture", self._hotkey_str)

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("HotkeyListener stopped")
     if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("HotkeyListener stopped")

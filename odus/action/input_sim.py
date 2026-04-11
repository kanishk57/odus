"""
Input Simulation — Pseudo keyboard & mouse control for agentic actions.

Provides a unified async API for simulating user input across X11 and Wayland.
Routes requests to the appropriate modular backend (ydotool, xdotool, pyautogui).
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from enum import Enum
from typing import Sequence

from odus.action.input.base import (
    InputActionType, InputActionResult, InputBackend,
)
from odus.action.input.ydotool import YdotoolBackend
from odus.action.input.xdotool import XdotoolBackend
from odus.action.input.pyautogui import PyAutoGUIBackend

logger = logging.getLogger(__name__)

class _Backend(Enum):
    PYAUTOGUI = "pyautogui"
    XDOTOOL = "xdotool"
    YDOTOOL = "ydotool"
    NONE = "none"

class InputSimulator:
    """
    Unified input controller. Automatically selects the best backend.
    """

    def __init__(self) -> None:
        self._session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self._focus_mode = self._get_focus_mode()
        self._mouse_backend_type = self._select_mouse_backend()
        self._keyboard_backend_type = self._select_keyboard_backend()
        
        self._mouse_impl = self._create_backend(self._mouse_backend_type)
        self._keyboard_impl = self._create_backend(self._keyboard_backend_type)

        logger.info(
            "InputSimulator initialized | session=%s | focus=%s | mouse=%s | keyboard=%s",
            self._session_type,
            self._focus_mode,
            self._mouse_backend_type.value,
            self._keyboard_backend_type.value,
        )

    def _get_focus_mode(self) -> str:
        """Detect system focus mode (e.g., GNOME sloppy focus)."""
        try:
            import subprocess
            res = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.wm.preferences", "focus-mode"],
                text=True, stderr=subprocess.DEV_NULL
            )
            return res.strip().strip("'")
        except Exception:
            return "click"

    def _create_backend(self, b_type: _Backend) -> InputBackend | None:
        if b_type == _Backend.YDOTOOL: return YdotoolBackend()
        if b_type == _Backend.XDOTOOL: return XdotoolBackend()
        if b_type == _Backend.PYAUTOGUI: return PyAutoGUIBackend()
        return None

    def _select_mouse_backend(self) -> _Backend:
        if self._session_type != "wayland":
            if self._has_pag(): return _Backend.PYAUTOGUI
            if shutil.which("xdotool"): return _Backend.XDOTOOL
        else:
            if shutil.which("ydotool"): return _Backend.YDOTOOL
            if shutil.which("xdotool"): return _Backend.XDOTOOL
            if self._has_pag(): return _Backend.PYAUTOGUI
        return _Backend.NONE

    def _select_keyboard_backend(self) -> _Backend:
        return self._select_mouse_backend() # Usually the same

    def _has_pag(self) -> bool:
        try:
            import pyautogui # noqa
            return True
        except ImportError:
            return False

    async def move_mouse(self, x: int, y: int) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._mouse_impl: raise RuntimeError("No mouse backend")
            await self._mouse_impl.move_mouse(x, y)
            return InputActionResult(InputActionType.MOUSE_MOVE, True, f"Moved to ({x}, {y})", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.MOUSE_MOVE, False, "Move failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def click(self, x: int, y: int, button: str = "left") -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._mouse_impl: raise RuntimeError("No mouse backend")
            
            # 🐢 Debug Slowdown: Move and then wait so user sees the cursor position
            await self._mouse_impl.move_mouse(x, y)
            await asyncio.sleep(1.0)
            
            await self._mouse_impl.click(x, y, button)
            return InputActionResult(InputActionType.MOUSE_CLICK, True, f"Clicked {button} at ({x}, {y})", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.MOUSE_CLICK, False, "Click failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def double_click(self, x: int, y: int) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._mouse_impl: raise RuntimeError("No mouse backend")
            
            # 🐢 Debug Slowdown
            await self._mouse_impl.move_mouse(x, y)
            await asyncio.sleep(1.0)
            
            await self._mouse_impl.double_click(x, y)
            return InputActionResult(InputActionType.MOUSE_DOUBLE_CLICK, True, f"Double-clicked at ({x}, {y})", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.MOUSE_DOUBLE_CLICK, False, "Double-click failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def right_click(self, x: int, y: int) -> InputActionResult:
        return await self.click(x, y, button="right")

    async def scroll(self, direction: str = "down", amount: int = 3) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._mouse_impl: raise RuntimeError("No mouse backend")
            await self._mouse_impl.scroll(direction, amount)
            return InputActionResult(InputActionType.MOUSE_SCROLL, True, f"Scrolled {direction}", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.MOUSE_SCROLL, False, "Scroll failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._mouse_impl: raise RuntimeError("No mouse backend")
            await self._mouse_impl.drag(x1, y1, x2, y2, duration)
            return InputActionResult(InputActionType.MOUSE_DRAG, True, f"Dragged from ({x1},{y1}) to ({x2},{y2})", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.MOUSE_DRAG, False, "Drag failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def _ensure_focus(self, x: int, y: int) -> None:
        """Aggressively force focus onto the target coordinates."""
        if not self._mouse_impl:
            return

        logger.debug("Aggressive focus attempt at (%d, %d)", x, y)
        
        # 1. Move to target + slight jitter to trigger hover-focus WMs
        await self._mouse_impl.move_mouse(x, y)
        await asyncio.sleep(0.1)
        await self._mouse_impl.move_mouse(x + 1, y + 1)
        await asyncio.sleep(0.1)
        await self._mouse_impl.move_mouse(x, y)
        await asyncio.sleep(0.2)
        
        # 2. Triple-click focus
        await self._mouse_impl.click(x, y, "left")
        await asyncio.sleep(0.1)
        await self._mouse_impl.click(x, y, "left")
        await asyncio.sleep(0.1)
        
        # 3. Wait for WM to settle
        await asyncio.sleep(0.5)

    async def type_text(self, text: str, interval: float = 0.1, x: int | None = None, y: int | None = None) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._keyboard_impl: raise RuntimeError("No keyboard backend")
            
            # 💡 Aggressive Focus Fix: If we have coordinates, force focus
            if x is not None and y is not None:
                await self._ensure_focus(x, y)
                
            await self._keyboard_impl.type_text(text[:500], interval, x=x, y=y)
            return InputActionResult(InputActionType.KEY_TYPE, True, f"Typed text", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.KEY_TYPE, False, "Type failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def press_key(self, key: str, x: int | None = None, y: int | None = None) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._keyboard_impl: raise RuntimeError("No keyboard backend")
            
            # 💡 Aggressive Focus Fix: If we have coordinates, force focus
            if x is not None and y is not None:
                await self._ensure_focus(x, y)
                
            await self._keyboard_impl.press_key(key, x=x, y=y)
            return InputActionResult(InputActionType.KEY_PRESS, True, f"Pressed {key}", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.KEY_PRESS, False, "Press failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    async def hotkey(self, *keys: str, x: int | None = None, y: int | None = None) -> InputActionResult:
        t0 = time.monotonic()
        try:
            if not self._keyboard_impl: raise RuntimeError("No keyboard backend")
            
            # 💡 Aggressive Focus Fix: If we have coordinates, force focus
            if x is not None and y is not None:
                await self._ensure_focus(x, y)
                
            await self._keyboard_impl.hotkey(keys, x=x, y=y)
            return InputActionResult(InputActionType.KEY_HOTKEY, True, f"Pressed hotkey {'+'.join(keys)}", duration_ms=(time.monotonic()-t0)*1000)
        except Exception as e:
            return InputActionResult(InputActionType.KEY_HOTKEY, False, "Hotkey failed", error=str(e), duration_ms=(time.monotonic()-t0)*1000)

    def get_capabilities(self) -> dict:
        m_healthy = not getattr(self._mouse_impl, "health_error", None) if self._mouse_impl else False
        k_healthy = not getattr(self._keyboard_impl, "health_error", None) if self._keyboard_impl else False
        
        return {
            "session_type": self._session_type,
            "focus_mode": self._focus_mode,
            "mouse_backend": self._mouse_backend_type.value,
            "keyboard_backend": self._keyboard_backend_type.value,
            "mouse_available": self._mouse_backend_type != _Backend.NONE,
            "keyboard_available": self._keyboard_backend_type != _Backend.NONE,
            "mouse_healthy": m_healthy,
            "keyboard_healthy": k_healthy,
        }

_sim_instance: InputSimulator | None = None

def get_input_simulator() -> InputSimulator:
    global _sim_instance
    if _sim_instance is None:
        _sim_instance = InputSimulator()
    return _sim_instance

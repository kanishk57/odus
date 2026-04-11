"""
Input Simulation — Pseudo keyboard & mouse control for agentic actions.

Provides a unified async API for simulating user input across X11 and Wayland.

Backend strategy:
  - X11 / XWayland: pyautogui (pure Python, zero setup)
  - Wayland: ydotool (mouse + keyboard), wtype (keyboard fallback)
  - Fallback: xdotool (X11 CLI wrapper)

All methods are async-safe (heavy ops run in threads) and return
structured InputActionResult objects for the agent verification loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

logger = logging.getLogger(__name__)


# ── Result Types ───────────────────────────────────────────────────────

class InputActionType(Enum):
    """All possible input simulation actions."""

    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_RIGHT_CLICK = "mouse_right_click"
    MOUSE_SCROLL = "mouse_scroll"
    MOUSE_DRAG = "mouse_drag"
    KEY_TYPE = "key_type"
    KEY_PRESS = "key_press"
    KEY_HOTKEY = "key_hotkey"
    HIGHLIGHT = "highlight"


@dataclass
class InputActionResult:
    """Outcome of a single input simulation action."""

    action_type: InputActionType
    success: bool
    description: str
    error: str = ""
    duration_ms: float = 0.0


# ── Backend Enum ───────────────────────────────────────────────────────

class _Backend(Enum):
    PYAUTOGUI = "pyautogui"
    XDOTOOL = "xdotool"
    YDOTOOL = "ydotool"
    NONE = "none"


# ── Input Simulator ───────────────────────────────────────────────────

class InputSimulator:
    """
    Pseudo-keyboard and mouse controller for agentic desktop actions.

    Automatically selects the best backend for the current display server.

    Usage:
        sim = InputSimulator()
        result = await sim.click(320, 450)
        result = await sim.type_text("hello world")
        result = await sim.press_key("enter")
        result = await sim.hotkey("ctrl", "s")
        result = await sim.scroll("down", 3)
    """

    def __init__(self) -> None:
        self._session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self._mouse_backend = self._select_mouse_backend()
        self._keyboard_backend = self._select_keyboard_backend()

        # Lazy-import pyautogui only when needed
        self._pyautogui = None

        logger.info(
            "InputSimulator initialized | session=%s | mouse=%s | keyboard=%s",
            self._session_type,
            self._mouse_backend.value,
            self._keyboard_backend.value,
        )

    # ── Backend Selection ──────────────────────────────────────────────

    def _select_mouse_backend(self) -> _Backend:
        """Pick the best mouse simulation backend."""
        if self._session_type != "wayland":
            # X11 — prefer pyautogui
            try:
                import pyautogui  # noqa: F401
                return _Backend.PYAUTOGUI
            except ImportError:
                pass
            if shutil.which("xdotool"):
                return _Backend.XDOTOOL

        else:
            # Wayland — prefer ydotool
            if shutil.which("ydotool"):
                return _Backend.YDOTOOL
            # xdotool sometimes works on XWayland apps
            if shutil.which("xdotool"):
                logger.warning("Wayland: ydotool not found, falling back to xdotool (limited)")
                return _Backend.XDOTOOL
            try:
                import pyautogui  # noqa: F401
                logger.warning("Wayland: using pyautogui (may not work on all compositors)")
                return _Backend.PYAUTOGUI
            except ImportError:
                pass

        logger.error("No mouse simulation backend available!")
        return _Backend.NONE

    def _select_keyboard_backend(self) -> _Backend:
        """Pick the best keyboard simulation backend."""
        if self._session_type != "wayland":
            try:
                import pyautogui  # noqa: F401
                return _Backend.PYAUTOGUI
            except ImportError:
                pass
            if shutil.which("xdotool"):
                return _Backend.XDOTOOL
        else:
            if shutil.which("ydotool"):
                return _Backend.YDOTOOL
            if shutil.which("xdotool"):
                return _Backend.XDOTOOL
            try:
                import pyautogui  # noqa: F401
                return _Backend.PYAUTOGUI
            except ImportError:
                pass

        logger.error("No keyboard simulation backend available!")
        return _Backend.NONE

    def _get_pyautogui(self):
        """Lazy import pyautogui to avoid import errors when not needed."""
        if self._pyautogui is None:
            import pyautogui
            pyautogui.FAILSAFE = True   # Move mouse to corner to abort
            pyautogui.PAUSE = 0.05      # Tiny pause between actions
            self._pyautogui = pyautogui
        return self._pyautogui

    # ── Mouse Actions ──────────────────────────────────────────────────

    async def move_mouse(self, x: int, y: int) -> InputActionResult:
        """Move the mouse cursor to (x, y) screen coordinates."""
        t0 = time.monotonic()
        try:
            await self._do_mouse_move(x, y)
            return InputActionResult(
                action_type=InputActionType.MOUSE_MOVE,
                success=True,
                description=f"Moved mouse to ({x}, {y})",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("move_mouse(%d, %d) failed: %s", x, y, e)
            return InputActionResult(
                action_type=InputActionType.MOUSE_MOVE,
                success=False,
                description=f"Failed to move mouse to ({x}, {y})",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def click(
        self, x: int, y: int, button: str = "left"
    ) -> InputActionResult:
        """Click at (x, y) with the specified button."""
        t0 = time.monotonic()
        try:
            await self._do_click(x, y, button)
            return InputActionResult(
                action_type=InputActionType.MOUSE_CLICK,
                success=True,
                description=f"{button.capitalize()}-clicked at ({x}, {y})",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("click(%d, %d, %s) failed: %s", x, y, button, e)
            return InputActionResult(
                action_type=InputActionType.MOUSE_CLICK,
                success=False,
                description=f"Failed to click at ({x}, {y})",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def double_click(self, x: int, y: int) -> InputActionResult:
        """Double-click at (x, y)."""
        t0 = time.monotonic()
        try:
            await self._do_double_click(x, y)
            return InputActionResult(
                action_type=InputActionType.MOUSE_DOUBLE_CLICK,
                success=True,
                description=f"Double-clicked at ({x}, {y})",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("double_click(%d, %d) failed: %s", x, y, e)
            return InputActionResult(
                action_type=InputActionType.MOUSE_DOUBLE_CLICK,
                success=False,
                description=f"Failed to double-click at ({x}, {y})",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def right_click(self, x: int, y: int) -> InputActionResult:
        """Right-click at (x, y)."""
        return await self.click(x, y, button="right")

    async def scroll(
        self, direction: str = "down", amount: int = 3
    ) -> InputActionResult:
        """Scroll the mouse wheel. direction: 'up', 'down', 'left', 'right'."""
        t0 = time.monotonic()
        try:
            await self._do_scroll(direction, amount)
            return InputActionResult(
                action_type=InputActionType.MOUSE_SCROLL,
                success=True,
                description=f"Scrolled {direction} by {amount}",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("scroll(%s, %d) failed: %s", direction, amount, e)
            return InputActionResult(
                action_type=InputActionType.MOUSE_SCROLL,
                success=False,
                description=f"Failed to scroll {direction}",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def drag(
        self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5
    ) -> InputActionResult:
        """Drag from (x1, y1) to (x2, y2)."""
        t0 = time.monotonic()
        try:
            await self._do_drag(x1, y1, x2, y2, duration)
            return InputActionResult(
                action_type=InputActionType.MOUSE_DRAG,
                success=True,
                description=f"Dragged from ({x1}, {y1}) to ({x2}, {y2})",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("drag failed: %s", e)
            return InputActionResult(
                action_type=InputActionType.MOUSE_DRAG,
                success=False,
                description=f"Failed to drag from ({x1}, {y1}) to ({x2}, {y2})",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Keyboard Actions ───────────────────────────────────────────────

    async def type_text(
        self, text: str, interval: float = 0.03
    ) -> InputActionResult:
        """Type a string of text character by character."""
        t0 = time.monotonic()
        # Truncate for safety
        safe_text = text[:500]
        try:
            await self._do_type_text(safe_text, interval)
            preview = safe_text[:60] + ("..." if len(safe_text) > 60 else "")
            return InputActionResult(
                action_type=InputActionType.KEY_TYPE,
                success=True,
                description=f"Typed: \"{preview}\"",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("type_text failed: %s", e)
            return InputActionResult(
                action_type=InputActionType.KEY_TYPE,
                success=False,
                description="Failed to type text",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def press_key(self, key: str) -> InputActionResult:
        """
        Press a single key or key name.

        Supported key names: enter, tab, escape, backspace, delete,
        space, up, down, left, right, home, end, pageup, pagedown,
        f1-f12, etc.
        """
        t0 = time.monotonic()
        try:
            await self._do_press_key(key)
            return InputActionResult(
                action_type=InputActionType.KEY_PRESS,
                success=True,
                description=f"Pressed key: {key}",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("press_key(%s) failed: %s", key, e)
            return InputActionResult(
                action_type=InputActionType.KEY_PRESS,
                success=False,
                description=f"Failed to press key: {key}",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    async def hotkey(self, *keys: str) -> InputActionResult:
        """
        Press a key combination (e.g., hotkey("ctrl", "s")).

        Modifier names: ctrl, shift, alt, super/meta/win.
        """
        t0 = time.monotonic()
        combo = "+".join(keys)
        try:
            await self._do_hotkey(keys)
            return InputActionResult(
                action_type=InputActionType.KEY_HOTKEY,
                success=True,
                description=f"Pressed hotkey: {combo}",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            logger.error("hotkey(%s) failed: %s", combo, e)
            return InputActionResult(
                action_type=InputActionType.KEY_HOTKEY,
                success=False,
                description=f"Failed to press hotkey: {combo}",
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Backend Implementations (Private) ──────────────────────────────

    async def _do_mouse_move(self, x: int, y: int) -> None:
        b = self._mouse_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            await asyncio.to_thread(pag.moveTo, x, y, duration=0.2)
        elif b == _Backend.XDOTOOL:
            await self._run_cmd(["xdotool", "mousemove", str(x), str(y)])
        elif b == _Backend.YDOTOOL:
            await self._run_cmd(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])
        else:
            raise RuntimeError("No mouse backend available")

    async def _do_click(self, x: int, y: int, button: str) -> None:
        b = self._mouse_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            await asyncio.to_thread(pag.click, x, y, button=button)
        elif b == _Backend.XDOTOOL:
            btn_map = {"left": "1", "middle": "2", "right": "3"}
            btn = btn_map.get(button, "1")
            await self._run_cmd(["xdotool", "mousemove", str(x), str(y)])
            await self._run_cmd(["xdotool", "click", btn])
        elif b == _Backend.YDOTOOL:
            btn_map = {"left": "0x00", "right": "0x01", "middle": "0x02"}
            btn = btn_map.get(button, "0x00")
            await self._run_cmd(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])
            await self._run_cmd(["ydotool", "click", btn])
        else:
            raise RuntimeError("No mouse backend available")

    async def _do_double_click(self, x: int, y: int) -> None:
        b = self._mouse_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            await asyncio.to_thread(pag.doubleClick, x, y)
        elif b == _Backend.XDOTOOL:
            await self._run_cmd(["xdotool", "mousemove", str(x), str(y)])
            await self._run_cmd(["xdotool", "click", "--repeat", "2", "1"])
        elif b == _Backend.YDOTOOL:
            await self._run_cmd(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])
            await self._run_cmd(["ydotool", "click", "0x00"])
            await asyncio.sleep(0.05)
            await self._run_cmd(["ydotool", "click", "0x00"])
        else:
            raise RuntimeError("No mouse backend available")

    async def _do_scroll(self, direction: str, amount: int) -> None:
        b = self._mouse_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            clicks = amount if direction in ("up", "left") else -amount
            if direction in ("up", "down"):
                await asyncio.to_thread(pag.scroll, clicks)
            else:
                await asyncio.to_thread(pag.hscroll, clicks)
        elif b == _Backend.XDOTOOL:
            if direction == "up":
                btn = "4"
            elif direction == "down":
                btn = "5"
            elif direction == "left":
                btn = "6"
            else:
                btn = "7"
            for _ in range(amount):
                await self._run_cmd(["xdotool", "click", btn])
        elif b == _Backend.YDOTOOL:
            # ydotool uses raw wheel values (positive = up, negative = down)
            if direction in ("down", "right"):
                amount = -amount
            await self._run_cmd(["ydotool", "mousemove", "-w", str(amount)])
        else:
            raise RuntimeError("No mouse backend available")

    async def _do_drag(
        self, x1: int, y1: int, x2: int, y2: int, duration: float
    ) -> None:
        b = self._mouse_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            await asyncio.to_thread(pag.moveTo, x1, y1)
            await asyncio.to_thread(pag.drag, x2 - x1, y2 - y1, duration=duration)
        elif b == _Backend.XDOTOOL:
            await self._run_cmd(["xdotool", "mousemove", str(x1), str(y1)])
            await self._run_cmd(["xdotool", "mousedown", "1"])
            await asyncio.sleep(0.1)
            await self._run_cmd(["xdotool", "mousemove", str(x2), str(y2)])
            await asyncio.sleep(0.1)
            await self._run_cmd(["xdotool", "mouseup", "1"])
        elif b == _Backend.YDOTOOL:
            await self._run_cmd(["ydotool", "mousemove", "--absolute", "-x", str(x1), "-y", str(y1)])
            await self._run_cmd(["ydotool", "click", "--next-delay", str(int(duration * 1000)), "0x40"])
            await self._run_cmd(["ydotool", "mousemove", "--absolute", "-x", str(x2), "-y", str(y2)])
            await self._run_cmd(["ydotool", "click", "0x80"])
        else:
            raise RuntimeError("No mouse backend available")

    async def _do_type_text(self, text: str, interval: float) -> None:
        b = self._keyboard_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            await asyncio.to_thread(pag.typewrite, text, interval=interval)
        elif b == _Backend.XDOTOOL:
            await self._run_cmd(["xdotool", "type", "--delay", str(int(interval * 1000)), text])
        elif b == _Backend.YDOTOOL:
            await self._run_cmd(["ydotool", "type", "--key-delay", str(int(interval * 1000)), text])
        else:
            raise RuntimeError("No keyboard backend available")

    async def _do_press_key(self, key: str) -> None:
        b = self._keyboard_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            await asyncio.to_thread(pag.press, key.lower())
        elif b == _Backend.XDOTOOL:
            xdo_key = self._map_key_xdotool(key)
            await self._run_cmd(["xdotool", "key", xdo_key])
        elif b == _Backend.YDOTOOL:
            ydo_key = self._map_key_ydotool(key)
            await self._run_cmd(["ydotool", "key", ydo_key])
        else:
            raise RuntimeError("No keyboard backend available")

    async def _do_hotkey(self, keys: Sequence[str]) -> None:
        b = self._keyboard_backend
        if b == _Backend.PYAUTOGUI:
            pag = self._get_pyautogui()
            mapped = [k.lower() for k in keys]
            await asyncio.to_thread(pag.hotkey, *mapped)
        elif b == _Backend.XDOTOOL:
            combo = "+".join(self._map_key_xdotool(k) for k in keys)
            await self._run_cmd(["xdotool", "key", combo])
        elif b == _Backend.YDOTOOL:
            # ydotool doesn't have native hotkey combo support — press modifiers individually
            # Press each key, then release in reverse
            for k in keys:
                await self._run_cmd(["ydotool", "key", f"{self._map_key_ydotool(k)}:1"])
            for k in reversed(keys):
                await self._run_cmd(["ydotool", "key", f"{self._map_key_ydotool(k)}:0"])
        else:
            raise RuntimeError("No keyboard backend available")

    # ── Key Mapping Helpers ────────────────────────────────────────────

    @staticmethod
    def _map_key_xdotool(key: str) -> str:
        """Map friendly key names to xdotool key names."""
        mapping = {
            "enter": "Return", "return": "Return",
            "tab": "Tab", "escape": "Escape", "esc": "Escape",
            "backspace": "BackSpace", "delete": "Delete",
            "space": "space",
            "up": "Up", "down": "Down", "left": "Left", "right": "Right",
            "home": "Home", "end": "End",
            "pageup": "Page_Up", "pagedown": "Page_Down",
            "ctrl": "ctrl", "shift": "shift", "alt": "alt",
            "super": "super", "meta": "super", "win": "super",
        }
        return mapping.get(key.lower(), key)

    @staticmethod
    def _map_key_ydotool(key: str) -> str:
        """Map friendly key names to ydotool keycodes (Linux KEY_* names)."""
        mapping = {
            "enter": "28", "return": "28",
            "tab": "15", "escape": "1", "esc": "1",
            "backspace": "14", "delete": "111",
            "space": "57",
            "up": "103", "down": "108", "left": "105", "right": "106",
            "home": "102", "end": "107",
            "pageup": "104", "pagedown": "109",
            "ctrl": "29", "shift": "42", "alt": "56",
            "super": "125", "meta": "125", "win": "125",
            # Letters (a-z)
            "a": "30", "b": "48", "c": "46", "d": "32", "e": "18",
            "f": "33", "g": "34", "h": "35", "i": "23", "j": "36",
            "k": "37", "l": "38", "m": "50", "n": "49", "o": "24",
            "p": "25", "q": "16", "r": "19", "s": "31", "t": "20",
            "u": "22", "v": "47", "w": "17", "x": "45", "y": "21",
            "z": "44",
            # Function keys
            "f1": "59", "f2": "60", "f3": "61", "f4": "62",
            "f5": "63", "f6": "64", "f7": "65", "f8": "66",
            "f9": "67", "f10": "68", "f11": "87", "f12": "88",
        }
        return mapping.get(key.lower(), key)

    # ── Utilities ──────────────────────────────────────────────────────

    @staticmethod
    async def _run_cmd(cmd: list[str], timeout: int = 5) -> str:
        """Run a CLI tool and return stdout. Raises on failure."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")

        if proc.returncode != 0:
            err = stderr.decode().strip() if stderr else "unknown error"
            raise RuntimeError(f"{cmd[0]} failed (rc={proc.returncode}): {err}")

        return stdout.decode().strip() if stdout else ""

    def get_capabilities(self) -> dict:
        """Return a summary of available input capabilities."""
        return {
            "session_type": self._session_type,
            "mouse_backend": self._mouse_backend.value,
            "keyboard_backend": self._keyboard_backend.value,
            "mouse_available": self._mouse_backend != _Backend.NONE,
            "keyboard_available": self._keyboard_backend != _Backend.NONE,
        }


# ── Singleton ──────────────────────────────────────────────────────────

_sim_instance: InputSimulator | None = None


def get_input_simulator() -> InputSimulator:
    """Return the global singleton InputSimulator."""
    global _sim_instance
    if _sim_instance is None:
        _sim_instance = InputSimulator()
    return _sim_instance

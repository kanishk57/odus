"""
Ydotool Backend — Wayland input simulation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from odus.action.input.base import run_cmd

logger = logging.getLogger(__name__)

# ── Key Mapping ────────────────────────────────────────────────────────

YDO_KEY_MAP = {
    "enter": "28", "return": "28",
    "tab": "15", "escape": "1", "esc": "1",
    "backspace": "14", "delete": "111",
    "space": "57",
    "up": "103", "down": "108", "left": "105", "right": "106",
    "home": "102", "end": "107",
    "pageup": "104", "pagedown": "109",
    "ctrl": "29", "shift": "42", "alt": "56",
    "super": "125", "meta": "125", "win": "125",
    "a": "30", "b": "48", "c": "46", "d": "32", "e": "18",
    "f": "33", "g": "34", "h": "35", "i": "23", "j": "36",
    "k": "37", "l": "38", "m": "50", "n": "49", "o": "24",
    "p": "25", "q": "16", "r": "19", "s": "31", "t": "20",
    "u": "22", "v": "47", "w": "17", "x": "45", "y": "21",
    "z": "44",
    "f1": "59", "f2": "60", "f3": "61", "f4": "62",
    "f5": "63", "f6": "64", "f7": "65", "f8": "66",
    "f9": "67", "f10": "68", "f11": "87", "f12": "88",
}

class YdotoolBackend:
    """Wayland input simulation using ydotool CLI."""

    def __init__(self):
        self._use_numeric_buttons = False
        self._supports_absolute = True
        self._health_error: str | None = None
        self._health_check_task = asyncio.create_task(self._check_health())

    @property
    def health_error(self) -> str | None:
        return self._health_error

    async def _check_health(self) -> None:
        try:
            # We try a simple command to check if ydotool is functional
            help_out = await run_cmd(["ydotool", "click", "--help"])
            
            if "ydotoold backend unavailable" in help_out:
                self._health_error = (
                    "ydotoold daemon is NOT running or unreachable.\n"
                    "Fix: Install it with 'sudo apt install ydotoold' (if on Ubuntu/Debian), then run:\n"
                    "sudo ydotoold --socket-path /tmp/ydotoolsok --socket-own $(id -u):$(id -g)"
                )
                logger.warning(self._health_error)
            
            self._use_numeric_buttons = "1: left" in help_out

            # Check if -a is supported for absolute movement
            try:
                # We expect this to fail or show an error message if -a is unsupported
                # Since ydotoool returns 0 even on error, we must check stderr/output
                test_out = await run_cmd(["ydotool", "mousemove", "-a", "0", "0"])
                if "unrecognised option" in test_out.lower() or "invalid option" in test_out.lower():
                    self._supports_absolute = False
                    logger.info("ydotool does NOT support -a (absolute mode). Using simulated absolute movement.")
            except Exception:
                self._supports_absolute = False
                logger.info("ydotool does NOT support -a. Using simulated absolute movement.")

        except Exception as e:
            self._health_error = (
                f"ydotool check failed: {e}\n"
                "Ensure ydotool is installed and you have permissions for /dev/uinput."
            )
            logger.error(self._health_error)
            self._use_numeric_buttons = False

    def _ensure_healthy(self):
        if self._health_error:
            raise RuntimeError(self._health_error)

    async def move_mouse(self, x: int, y: int) -> None:
        self._ensure_healthy()
        
        if self._supports_absolute:
            try:
                await run_cmd(["ydotool", "mousemove", "-a", str(x), str(y)])
                return
            except Exception as e:
                logger.warning("Absolute mouse move failed, falling back to simulation: %s", e)
                # Fall through to simulation
        
        # Simulated Absolute Movement: 
        # 1. Reset to top-left (0,0) by moving extremely far up/left
        # 2. Move relatively to the target x,y
        logger.debug("Simulating absolute move to %d, %d", x, y)
        await run_cmd(["ydotool", "mousemove", "-99999", "-99999"])
        await asyncio.sleep(0.05)
        await run_cmd(["ydotool", "mousemove", str(x), str(y)])

    async def click(self, x: int, y: int, button: str) -> None:
        self._ensure_healthy()
        await self.move_mouse(x, y)
        await asyncio.sleep(0.1) # Wait for hover-focus to settle
        if self._use_numeric_buttons:
            btn_map = {"left": "1", "right": "2", "middle": "3"}
        else:
            btn_map = {"left": "0x01", "right": "0x02", "middle": "0x04"}
        btn = btn_map.get(button, "1" if self._use_numeric_buttons else "0x01")
        await run_cmd(["ydotool", "click", btn])

    async def double_click(self, x: int, y: int) -> None:
        self._ensure_healthy()
        await self.click(x, y, "left")
        await asyncio.sleep(0.1)
        await self.click(x, y, "left")

    async def scroll(self, direction: str, amount: int) -> None:
        self._ensure_healthy()
        val = amount if direction in ("up", "left") else -amount
        if direction in ("up", "down"):
            await run_cmd(["ydotool", "mousemove", "-w", "0", str(val)])
        else:
            await run_cmd(["ydotool", "mousemove", "-w", str(val), "0"])

    async def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float) -> None:
        self._ensure_healthy()
        await self.move_mouse(x1, y1)
        await run_cmd(["ydotool", "key", "272:1"]) # BTN_LEFT down
        await asyncio.sleep(0.1)
        await self.move_mouse(x2, y2)
        await asyncio.sleep(duration)
        await run_cmd(["ydotool", "key", "272:0"]) # BTN_LEFT up

    async def type_text(self, text: str, interval: float, x: int | None = None, y: int | None = None) -> None:
        self._ensure_healthy()
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1) # Wait for focus to shift
        
        # ydotool type can be sensitive to specials; we wrap it carefully
        await run_cmd(["ydotool", "type", "--key-delay", str(int(interval * 1000)), text])

    async def press_key(self, key: str, x: int | None = None, y: int | None = None) -> None:
        self._ensure_healthy()
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        ydo_key = YDO_KEY_MAP.get(key.lower(), key)
        await run_cmd(["ydotool", "key", ydo_key])

    async def hotkey(self, keys: Sequence[str], x: int | None = None, y: int | None = None) -> None:
        self._ensure_healthy()
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        cmd = ["ydotool", "key"]
        for k in keys:
            cmd.append(f"{YDO_KEY_MAP.get(k.lower(), k)}:1")
        for k in reversed(keys):
            cmd.append(f"{YDO_KEY_MAP.get(k.lower(), k)}:0")
        await run_cmd(cmd)

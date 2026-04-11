"""
Xdotool Backend — X11 input simulation via CLI.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from odus.action.input.base import run_cmd

logger = logging.getLogger(__name__)

# ── Key Mapping ────────────────────────────────────────────────────────

XDO_KEY_MAP = {
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

class XdotoolBackend:
    """X11 input simulation using xdotool CLI."""

    async def move_mouse(self, x: int, y: int) -> None:
        await run_cmd(["xdotool", "mousemove", str(x), str(y)])

    async def click(self, x: int, y: int, button: str) -> None:
        btn_map = {"left": "1", "middle": "2", "right": "3"}
        btn = btn_map.get(button, "1")
        await self.move_mouse(x, y)
        await run_cmd(["xdotool", "click", btn])

    async def double_click(self, x: int, y: int) -> None:
        await self.move_mouse(x, y)
        await run_cmd(["xdotool", "click", "--repeat", "2", "1"])

    async def scroll(self, direction: str, amount: int) -> None:
        if direction == "up": btn = "4"
        elif direction == "down": btn = "5"
        elif direction == "left": btn = "6"
        else: btn = "7"
        for _ in range(amount):
            await run_cmd(["xdotool", "click", btn])

    async def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float) -> None:
        await self.move_mouse(x1, y1)
        await run_cmd(["xdotool", "mousedown", "1"])
        await asyncio.sleep(0.1)
        await self.move_mouse(x2, y2)
        await asyncio.sleep(duration)
        await run_cmd(["xdotool", "mouseup", "1"])

    async def type_text(self, text: str, interval: float, x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        await run_cmd(["xdotool", "type", "--delay", str(int(interval * 1000)), text])

    async def press_key(self, key: str, x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        xdo_key = XDO_KEY_MAP.get(key.lower(), key)
        await run_cmd(["xdotool", "key", xdo_key])

    async def hotkey(self, keys: Sequence[str], x: int | None = None, y: int | None = None) -> None:
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        combo = "+".join(XDO_KEY_MAP.get(k.lower(), k) for k in keys)
        await run_cmd(["xdotool", "key", combo])

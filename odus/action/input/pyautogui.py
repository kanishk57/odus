"""
PyAutoGUI Backend — Native cross-platform input simulation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

logger = logging.getLogger(__name__)

class PyAutoGUIBackend:
    """Native input simulation using pyautogui."""

    def __init__(self):
        self._pag = None

    def _get_pag(self):
        if self._pag is None:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            self._pag = pyautogui
        return self._pag

    async def move_mouse(self, x: int, y: int) -> None:
        pag = self._get_pag()
        await asyncio.to_thread(pag.moveTo, x, y, duration=0.2)

    async def click(self, x: int, y: int, button: str) -> None:
        pag = self._get_pag()
        await asyncio.to_thread(pag.click, x, y, button=button)

    async def double_click(self, x: int, y: int) -> None:
        pag = self._get_pag()
        await asyncio.to_thread(pag.doubleClick, x, y)

    async def scroll(self, direction: str, amount: int) -> None:
        pag = self._get_pag()
        clicks = amount if direction in ("up", "left") else -amount
        if direction in ("up", "down"):
            await asyncio.to_thread(pag.scroll, clicks)
        else:
            await asyncio.to_thread(pag.hscroll, clicks)

    async def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float) -> None:
        pag = self._get_pag()
        await asyncio.to_thread(pag.moveTo, x1, y1)
        await asyncio.to_thread(pag.drag, x2 - x1, y2 - y1, duration=duration)

    async def type_text(self, text: str, interval: float, x: int | None = None, y: int | None = None) -> None:
        pag = self._get_pag()
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        await asyncio.to_thread(pag.typewrite, text, interval=interval)

    async def press_key(self, key: str, x: int | None = None, y: int | None = None) -> None:
        pag = self._get_pag()
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        await asyncio.to_thread(pag.press, key.lower())

    async def hotkey(self, keys: Sequence[str], x: int | None = None, y: int | None = None) -> None:
        pag = self._get_pag()
        if x is not None and y is not None:
            await self.move_mouse(x, y)
            await asyncio.sleep(0.1)
        mapped = [k.lower() for k in keys]
        await asyncio.to_thread(pag.hotkey, *mapped)

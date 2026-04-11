"""
Input Simulation Base — Types and interfaces for input backends.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Protocol

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


class InputBackend(Protocol):
    """Protocol for input simulation backends."""

    async def move_mouse(self, x: int, y: int) -> None: ...
    async def click(self, x: int, y: int, button: str) -> None: ...
    async def double_click(self, x: int, y: int) -> None: ...
    async def scroll(self, direction: str, amount: int) -> None: ...
    async def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float) -> None: ...
    async def type_text(self, text: str, interval: float, x: int | None = None, y: int | None = None) -> None: ...
    async def press_key(self, key: str, x: int | None = None, y: int | None = None) -> None: ...
    async def hotkey(self, keys: Sequence[str], x: int | None = None, y: int | None = None) -> None: ...

async def run_cmd(cmd: list[str], timeout: int = 5) -> str:
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
        err_msg = stderr.decode().strip() if stderr else "unknown error"
        raise RuntimeError(f"Command '{' '.join(cmd)}' failed with exit code {proc.returncode}: {err_msg}")

    return stdout.decode().strip() if stdout else ""

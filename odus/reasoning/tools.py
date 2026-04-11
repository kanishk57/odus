"""
Tool Definitions — runtime wrappers for function-calling tools.

DEV 2 owns this module.

These are the Python implementations of the tools declared in prompts.py.
The agent calls these after the Vision API requests a function call.

Includes CLI tools (streaming), File tools (sandboxed), and desktop control tools.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator

from odus.action.pty_session import PtySession
from odus.action.file_browser import FileBrowser, FileEntry
from odus.action.safety import SafetyGate, SafetyVerdict
from odus.action.input_sim import get_input_simulator, InputActionResult
from odus.events import OdusEvent, EventType, get_event_bus

logger = logging.getLogger(__name__)

# Singleton instances (lazy-initialized)
_pty: PtySession | None = None
_browser: FileBrowser | None = None
_safety: SafetyGate | None = None


def get_pty() -> PtySession:
    global _pty
    if _pty is None:
        _pty = PtySession()
    return _pty


def get_browser() -> FileBrowser:
    global _browser
    if _browser is None:
        _browser = FileBrowser()
    return _browser


def get_safety() -> SafetyGate:
    global _safety
    if _safety is None:
        _safety = SafetyGate()
    return _safety


async def _emit(event_type: EventType, payload: dict = None):
    await get_event_bus().emit(OdusEvent(event_type, payload or {}))


# ── CLI & Terminal Tools ────────────────────────────────────────────────

async def tool_run_command(
    command: str,
    safety_tier: int,
    explanation: str,
) -> dict:
    """
    Execute a CLI command in a real PTY with real-time streaming output.
    """
    safety = get_safety()
    pty = get_pty()

    # Safety check
    verdict = safety.classify(command)

    if verdict == SafetyVerdict.BLOCKED:
        logger.warning("🚫 BLOCKED command: %s", command)
        return {
            "status": "blocked",
            "reason": "This command was classified as dangerous and was NOT executed.",
            "command": command,
            "explanation": explanation,
        }

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        return {
            "status": "needs_confirmation",
            "command": command,
            "explanation": explanation,
            "safety_tier": 2,
        }

    # Tier 1 — auto-execute
    await _emit(EventType.TERMINAL_COMMAND_STARTED, {"command": command})
    
    full_output = []
    async for line in pty.execute(command):
        full_output.append(line)
        await _emit(EventType.TERMINAL_OUTPUT_LINE, {"line": line})

    # Check if CWD changed
    await _emit(EventType.TERMINAL_CWD_CHANGED, {"cwd": pty.cwd})
    await _emit(EventType.TERMINAL_COMMAND_DONE, {"command": command, "exit_code": 0})

    return {
        "status": "executed",
        "command": command,
        "output": "\n".join(full_output),
        "cwd": pty.cwd,
    }


# ── File Tools ──────────────────────────────────────────────────────────

async def tool_list_directory(
    path: str,
    explanation: str,
) -> dict:
    """List files in a directory, checking permissions first."""
    browser = get_browser()
    
    if browser.needs_permission(path):
        return {
            "status": "needs_permission",
            "resource_type": "directory",
            "path": path,
            "description": explanation,
        }
    
    try:
        entries = await browser.list_directory(path)
        return {
            "status": "success",
            "path": path,
            "entries": [
                {"name": e.name, "is_dir": e.is_dir, "size": e.size}
                for e in entries
            ],
            "explanation": explanation,
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


async def tool_read_file(
    path: str,
    explanation: str,
) -> dict:
    """Read a file's content, checking permissions first."""
    browser = get_browser()
    
    # Resolve parent dir for permission check
    abs_path = os.path.abspath(os.path.expanduser(path))
    parent = os.path.dirname(abs_path)

    if browser.needs_permission(parent):
        return {
            "status": "needs_permission",
            "resource_type": "file",
            "path": path,
            "parent_path": parent,
            "description": explanation,
        }
        
    try:
        content = await browser.read_file(path)
        return {
            "status": "success",
            "path": path,
            "content": content,
            "explanation": explanation,
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


# ── Desktop Control Tools ──────────────────────────────────────────────

async def tool_move_and_click(
    x: int,
    y: int,
    target_description: str,
    safety_tier: int,
    explanation: str,
    button: str = "left",
    click_type: str = "single",
) -> dict:
    """Move mouse and click, checking safety gate."""
    safety = get_safety()
    verdict = safety.classify_input_action("click", target_description)

    if verdict == SafetyVerdict.BLOCKED:
        return {
            "status": "blocked",
            "reason": f"Click on '{target_description}' was blocked for safety.",
        }

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        return {
            "status": "needs_confirmation",
            "action_type": "move_and_click",
            "x": x, "y": y, "button": button, "click_type": click_type,
            "target_description": target_description,
            "explanation": explanation,
        }

    sim = get_input_simulator()
    if click_type == "double":
        result = await sim.double_click(x, y)
    elif button == "right":
        result = await sim.right_click(x, y)
    else:
        result = await sim.click(x, y, button=button)

    return _format_input_result(result, explanation)


async def tool_type_text(
    text: str,
    target_description: str,
    safety_tier: int,
    explanation: str,
) -> dict:
    """Type text, always requiring confirmation if cautioned."""
    safety = get_safety()
    verdict = safety.classify_input_action("type_text", target_description)

    if verdict == SafetyVerdict.BLOCKED:
        return {"status": "blocked", "reason": "Typing here is blocked."}

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        return {
            "status": "needs_confirmation",
            "action_type": "type_text",
            "text": text,
            "target_description": target_description,
            "explanation": explanation,
        }

    sim = get_input_simulator()
    result = await sim.type_text(text)
    return _format_input_result(result, explanation)


async def tool_press_key(
    keys: list[str],
    target_description: str,
    safety_tier: int,
    explanation: str,
) -> dict:
    """Press keyboard keys."""
    safety = get_safety()
    verdict = safety.classify_input_action("press_key", target_description)

    if verdict == SafetyVerdict.BLOCKED:
        return {"status": "blocked", "reason": "Key press blocked."}

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        return {
            "status": "needs_confirmation",
            "action_type": "press_key",
            "keys": keys,
            "target_description": target_description,
            "explanation": explanation,
        }

    sim = get_input_simulator()
    if len(keys) == 1:
        result = await sim.press_key(keys[0])
    else:
        result = await sim.hotkey(*keys)
    return _format_input_result(result, explanation)


async def tool_scroll_screen(
    direction: str,
    explanation: str,
    amount: int = 3,
) -> dict:
    """Scroll the screen."""
    sim = get_input_simulator()
    result = await sim.scroll(direction, amount)
    return _format_input_result(result, explanation)


async def tool_highlight_area(
    x: int,
    y: int,
    width: int,
    height: int,
    explanation: str,
) -> dict:
    """Visual highlight."""
    return {
        "status": "highlight",
        "action_type": "highlight_area",
        "x": x, "y": y, "width": width, "height": height,
        "explanation": explanation,
    }


def tool_explain(topic: str, explanation: str) -> dict:
    return {"status": "explained", "topic": topic, "explanation": explanation}


def tool_suggest_fix(command: str, safety_tier: int, explanation: str, risk_warning: str = "") -> dict:
    return {
        "status": "needs_confirmation",
        "command": command,
        "safety_tier": safety_tier,
        "explanation": explanation,
        "risk_warning": risk_warning,
    }


def _format_input_result(result: InputActionResult, explanation: str) -> dict:
    return {
        "status": "executed" if result.success else "failed",
        "action_type": result.action_type.value,
        "description": result.description,
        "error": result.error,
        "explanation": explanation,
    }

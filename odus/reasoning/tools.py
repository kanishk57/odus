"""
Tool Definitions — runtime wrappers for function-calling tools.

DEV 2 owns this module.

These are the Python implementations of the tools declared in prompts.py.
The agent calls these after the Vision API requests a function call.

Includes both CLI tools and desktop control (input simulation) tools.
"""

from __future__ import annotations

import logging

from odus.action.executor import CommandExecutor, ExecutionResult
from odus.action.safety import SafetyGate, SafetyVerdict
from odus.action.input_sim import get_input_simulator, InputActionResult

logger = logging.getLogger(__name__)

# Singleton instances (lazy-initialized)
_executor: CommandExecutor | None = None
_safety: SafetyGate | None = None


def _get_executor() -> CommandExecutor:
    global _executor
    if _executor is None:
        _executor = CommandExecutor()
    return _executor


def _get_safety() -> SafetyGate:
    global _safety
    if _safety is None:
        _safety = SafetyGate()
    return _safety


# ── CLI Tools ──────────────────────────────────────────────────────────

def tool_run_command(
    command: str,
    safety_tier: int,
    explanation: str,
) -> dict:
    """
    Execute a CLI command through the safety gate.

    Returns a dict with execution results and safety verdict.
    """
    safety = _get_safety()
    executor = _get_executor()

    # Double-check safety: model's tier vs our regex classifier
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
        # Return a signal that the UI should show a confirmation dialog
        return {
            "status": "needs_confirmation",
            "command": command,
            "explanation": explanation,
            "safety_tier": 2,
        }

    # Tier 1 — safe, auto-execute
    result: ExecutionResult = executor.run(command)
    return {
        "status": "executed",
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.return_code,
        "timed_out": result.timed_out,
    }


def tool_explain(topic: str, explanation: str) -> dict:
    """Provide an educational explanation without executing anything."""
    return {
        "status": "explained",
        "topic": topic,
        "explanation": explanation,
    }


def tool_suggest_fix(
    command: str,
    safety_tier: int,
    explanation: str,
    risk_warning: str = "",
) -> dict:
    """Suggest a fix that needs user confirmation before execution."""
    return {
        "status": "needs_confirmation",
        "command": command,
        "safety_tier": safety_tier,
        "explanation": explanation,
        "risk_warning": risk_warning,
    }


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
    """
    Move the mouse and click at screen coordinates.

    Checks safety gate before executing. Returns action result.
    """
    safety = _get_safety()
    verdict = safety.classify_input_action("click", target_description)

    if verdict == SafetyVerdict.BLOCKED:
        logger.warning("🚫 BLOCKED click on: %s", target_description)
        return {
            "status": "blocked",
            "action_type": "move_and_click",
            "reason": f"Click on '{target_description}' was blocked for safety.",
            "explanation": explanation,
        }

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        return {
            "status": "needs_confirmation",
            "action_type": "move_and_click",
            "x": x, "y": y,
            "button": button,
            "click_type": click_type,
            "target_description": target_description,
            "safety_tier": 2,
            "explanation": explanation,
        }

    # Safe — execute directly
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
    """
    Type text into the focused element.

    Always requires confirmation since it modifies state.
    """
    safety = _get_safety()
    verdict = safety.classify_input_action("type_text", target_description)

    if verdict == SafetyVerdict.BLOCKED:
        logger.warning("🚫 BLOCKED type_text on: %s", target_description)
        return {
            "status": "blocked",
            "action_type": "type_text",
            "reason": f"Typing in '{target_description}' was blocked for safety.",
            "explanation": explanation,
        }

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        preview = text[:60] + ("..." if len(text) > 60 else "")
        return {
            "status": "needs_confirmation",
            "action_type": "type_text",
            "text": text,
            "text_preview": preview,
            "target_description": target_description,
            "safety_tier": 2,
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
    """
    Press a key or key combination.

    Single keys: ["enter"], ["tab"], ["escape"]
    Combos: ["ctrl", "s"], ["ctrl", "shift", "t"]
    """
    safety = _get_safety()
    verdict = safety.classify_input_action("press_key", target_description)

    if verdict == SafetyVerdict.BLOCKED:
        logger.warning("🚫 BLOCKED press_key on: %s", target_description)
        return {
            "status": "blocked",
            "action_type": "press_key",
            "reason": f"Key press on '{target_description}' was blocked for safety.",
            "explanation": explanation,
        }

    if verdict == SafetyVerdict.NEEDS_CONFIRMATION:
        combo = "+".join(keys)
        return {
            "status": "needs_confirmation",
            "action_type": "press_key",
            "keys": keys,
            "combo": combo,
            "target_description": target_description,
            "safety_tier": 2,
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
    """
    Scroll the screen. Always safe — no safety gate needed.
    """
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
    """
    Draw a visual highlight on the screen.

    This is purely visual and always safe.
    Returns coordinates for the UI overlay to render.
    """
    return {
        "status": "highlight",
        "action_type": "highlight_area",
        "x": x, "y": y,
        "width": width, "height": height,
        "explanation": explanation,
    }


# ── Helpers ────────────────────────────────────────────────────────────

def _format_input_result(result: InputActionResult, explanation: str) -> dict:
    """Convert an InputActionResult to a tool response dict."""
    return {
        "status": "executed" if result.success else "failed",
        "action_type": result.action_type.value,
        "description": result.description,
        "error": result.error,
        "duration_ms": result.duration_ms,
        "explanation": explanation,
    }

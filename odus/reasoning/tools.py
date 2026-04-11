"""
Tool Definitions — runtime wrappers for function-calling tools.

DEV 2 owns this module.

These are the Python implementations of the tools declared in prompts.py.
The agent calls these after the Vision API requests a function call.
"""

from __future__ import annotations

import logging

from odus.action.executor import CommandExecutor, ExecutionResult
from odus.action.safety import SafetyGate, SafetyVerdict

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

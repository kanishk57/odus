"""
Agentic Loop — Observe → Think → Plan → Act → Verify → Repeat.

DEV 2 owns this module.

The Agent listens for events, runs Vision analysis, creates multi-step
action plans (CLI commands + desktop control), and executes them
step-by-step with verification screenshots between steps.
"""

from __future__ import annotations

import asyncio
import logging
import time

from odus.events import EventType, OdusEvent, get_event_bus
from odus.perception.capture import ScreenCapture
from odus.reasoning.tools import (
    tool_run_command,
    tool_explain,
    tool_suggest_fix,
    tool_move_and_click,
    tool_type_text,
    tool_press_key,
    tool_scroll_screen,
    tool_highlight_area,
)
from odus.reasoning.vision import VisionAnalyzer, AnalysisResult

logger = logging.getLogger(__name__)

# Minimum seconds between captures (prevents runaway loops)
_CAPTURE_COOLDOWN = 3.0

# Desktop control tool names (from prompts.py)
_INPUT_TOOLS = frozenset({
    "move_and_click", "type_text", "press_key",
    "scroll_screen", "highlight_area",
})

# CLI tool names
_CLI_TOOLS = frozenset({
    "run_command", "explain", "suggest_fix",
})


class Agent:
    """
    The Odus agentic loop.

    Lifecycle:
        1. Listens for CAPTURE_DONE or user query events on the bus.
        2. Captures the screen + sends to Gemini Vision for analysis.
        3. Receives a multi-step plan from Gemini.
        4. Emits AGENT_PLAN_CREATED with the full plan.
        5. Executes each step:
           a. Emits AGENT_STEP_STARTED
           b. Routes to the correct tool (CLI or desktop control)
           c. Emits AGENT_STEP_DONE or INPUT_ACTION_FAILED
           d. For desktop actions: takes a verification screenshot
        6. Emits AGENT_PLAN_DONE when all steps are finished.
        7. Waits for the next event.
    """

    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._vision = VisionAnalyzer()
        self._capture = ScreenCapture()
        self._running = False
        self._capturing = False          # Guard against concurrent captures
        self._last_capture_time = 0.0    # Debounce rapid capture requests

        logger.info("Agent initialized")

    async def start(self) -> None:
        """Start the agentic loop. Runs until stop() is called."""
        self._running = True

        # One-time setup (e.g., PipeWire ScreenCast consent dialog)
        try:
            await self._capture.initialize()
        except Exception as e:
            logger.warning("Capture initialization warning: %s", e)

        listener = self._bus.listen()

        logger.info("Agent loop started — waiting for events...")

        async for event in listener:
            if not self._running:
                break

            if event.type == EventType.CAPTURE_STARTED:
                query = event.payload.get("query", "") if event.payload else ""
                await self._handle_capture(query)

            elif event.type == EventType.USER_CONFIRMED:
                await self._handle_user_confirmed(event.payload)

            elif event.type == EventType.INPUT_ACTION_CONFIRMED:
                await self._handle_input_action_confirmed(event.payload)

    async def stop(self) -> None:
        """Stop the agentic loop."""
        self._running = False
        logger.info("Agent loop stopped")

    # ── Capture + Analysis Pipeline ────────────────────────────────────

    async def _handle_capture(self, query: str = "") -> None:
        """Full capture → analyze → plan → act pipeline with debounce + guard."""

        # ── Guard: skip if already capturing ──
        if self._capturing:
            logger.debug("Capture already in progress — ignoring duplicate event")
            return

        # ── Debounce: enforce cooldown between captures ──
        now = time.monotonic()
        elapsed = now - self._last_capture_time
        if elapsed < _CAPTURE_COOLDOWN:
            remaining = _CAPTURE_COOLDOWN - elapsed
            logger.debug("Capture cooldown: %.1fs remaining — skipping", remaining)
            return

        self._capturing = True
        self._last_capture_time = time.monotonic()

        try:
            # 1. CAPTURE
            logger.info("📸 Capturing screen...")
            result = await self._capture.grab_full_screen()
            compressed = self._capture.compress(result.png_bytes)

            await self._bus.emit(
                OdusEvent(EventType.CAPTURE_DONE, {
                    "width": result.width,
                    "height": result.height,
                    "size_bytes": len(compressed),
                })
            )

            # 2. ANALYZE
            await self._bus.emit(OdusEvent(EventType.ANALYSIS_STARTED))
            logger.info("🧠 Analyzing with Gemini Vision...")

            analysis = await self._vision.analyze(compressed, user_context=query)

            # 3. DECIDE & ACT
            await self._process_analysis(analysis)

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            await self._bus.emit(
                OdusEvent(EventType.ERROR, {"message": str(e)})
            )

        finally:
            self._capturing = False

    # ── Analysis Processing ────────────────────────────────────────────

    async def _process_analysis(self, analysis: AnalysisResult) -> None:
        """Route the analysis result — now supports multi-step plans."""

        # Check if the new plan-based format is available
        if analysis.plan:
            await self._process_plan(analysis)
            return

        # Legacy path: single suggested_commands (backward-compatible)
        if not analysis.suggested_commands:
            # No action needed — just explain
            await self._bus.emit(
                OdusEvent(EventType.ANALYSIS_DONE, {
                    "summary": analysis.summary,
                    "explanation": analysis.explanation_for_user,
                    "commands": [],
                    "confidence": analysis.confidence,
                    "follow_up": analysis.follow_up_hint,
                })
            )
            return

        for cmd in analysis.suggested_commands:
            if cmd.safety_tier == 1:
                # Auto-execute safe commands
                await self._bus.emit(OdusEvent(EventType.EXECUTION_STARTED))
                result = tool_run_command(
                    cmd.command, cmd.safety_tier, cmd.description
                )
                await self._bus.emit(
                    OdusEvent(EventType.EXECUTION_DONE, {
                        "summary": analysis.summary,
                        "explanation": analysis.explanation_for_user,
                        "result": result,
                        "confidence": analysis.confidence,
                    })
                )

            elif cmd.safety_tier == 2:
                # Needs user confirmation
                await self._bus.emit(
                    OdusEvent(EventType.CONFIRM_REQUIRED, {
                        "summary": analysis.summary,
                        "explanation": analysis.explanation_for_user,
                        "command": cmd.command,
                        "description": cmd.description,
                        "safety_tier": cmd.safety_tier,
                        "confidence": analysis.confidence,
                    })
                )

            else:
                # Tier 3 — blocked
                await self._bus.emit(
                    OdusEvent(EventType.ANALYSIS_DONE, {
                        "summary": analysis.summary,
                        "explanation": analysis.explanation_for_user,
                        "commands": [],
                        "blocked_command": cmd.command,
                        "confidence": analysis.confidence,
                        "warning": (
                            f"⚠️ Command '{cmd.command}' was classified as "
                            f"DANGEROUS and was blocked for your safety."
                        ),
                    })
                )

    # ── Multi-Step Plan Execution ──────────────────────────────────────

    async def _process_plan(self, analysis: AnalysisResult) -> None:
        """Execute a multi-step action plan from the new format."""

        plan = analysis.plan
        total_steps = len(plan)

        logger.info("📋 Received %d-step action plan", total_steps)

        # Emit the full plan to the UI
        await self._bus.emit(
            OdusEvent(EventType.AGENT_PLAN_CREATED, {
                "summary": analysis.summary,
                "explanation": analysis.explanation_for_user,
                "plan": plan,
                "total_steps": total_steps,
                "confidence": analysis.confidence,
            })
        )

        # Execute each step
        for i, step in enumerate(plan, start=1):
            action_type = step.get("action_type", "")
            params = step.get("params", {})
            description = step.get("description", "")
            safety_tier = step.get("safety_tier", 2)

            logger.info("▶ Step %d/%d: %s — %s", i, total_steps, action_type, description)

            await self._bus.emit(
                OdusEvent(EventType.AGENT_STEP_STARTED, {
                    "step": i,
                    "total_steps": total_steps,
                    "action_type": action_type,
                    "description": description,
                    "params": params,
                })
            )

            try:
                result = await self._execute_step(action_type, params, safety_tier, description)

                # If the step needs user confirmation, stop here and wait
                if result and result.get("status") == "needs_confirmation":
                    await self._bus.emit(
                        OdusEvent(EventType.INPUT_ACTION_PLANNED, {
                            "step": i,
                            "total_steps": total_steps,
                            "action": result,
                            "remaining_plan": plan[i:],
                        })
                    )
                    # The plan will resume when INPUT_ACTION_CONFIRMED is received
                    return

                if result and result.get("status") == "blocked":
                    await self._bus.emit(
                        OdusEvent(EventType.INPUT_ACTION_FAILED, {
                            "step": i,
                            "total_steps": total_steps,
                            "reason": result.get("reason", "Action blocked by safety gate."),
                        })
                    )
                    # Stop the plan — a blocked step halts everything
                    return

                # Step succeeded
                await self._bus.emit(
                    OdusEvent(EventType.AGENT_STEP_DONE, {
                        "step": i,
                        "total_steps": total_steps,
                        "action_type": action_type,
                        "description": description,
                        "result": result,
                    })
                )

                # Brief pause between steps for the desktop to settle
                if i < total_steps and action_type in _INPUT_TOOLS:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error("Step %d/%d failed: %s", i, total_steps, e, exc_info=True)
                await self._bus.emit(
                    OdusEvent(EventType.INPUT_ACTION_FAILED, {
                        "step": i,
                        "total_steps": total_steps,
                        "reason": str(e),
                    })
                )
                return  # Stop plan on error

        # All steps completed
        await self._bus.emit(
            OdusEvent(EventType.AGENT_PLAN_DONE, {
                "summary": analysis.summary,
                "total_steps": total_steps,
            })
        )

    async def _execute_step(
        self,
        action_type: str,
        params: dict,
        safety_tier: int,
        description: str,
    ) -> dict:
        """Route a single plan step to the correct tool."""

        if action_type == "run_command":
            return tool_run_command(
                command=params.get("command", ""),
                safety_tier=safety_tier,
                explanation=description,
            )

        elif action_type == "explain":
            return tool_explain(
                topic=params.get("topic", ""),
                explanation=description,
            )

        elif action_type == "suggest_fix":
            return tool_suggest_fix(
                command=params.get("command", ""),
                safety_tier=safety_tier,
                explanation=description,
                risk_warning=params.get("risk_warning", ""),
            )

        elif action_type == "move_and_click":
            return await tool_move_and_click(
                x=params.get("x", 0),
                y=params.get("y", 0),
                target_description=params.get("target_description", description),
                safety_tier=safety_tier,
                explanation=description,
                button=params.get("button", "left"),
                click_type=params.get("click_type", "single"),
            )

        elif action_type == "type_text":
            return await tool_type_text(
                text=params.get("text", ""),
                target_description=params.get("target_description", description),
                safety_tier=safety_tier,
                explanation=description,
            )

        elif action_type == "press_key":
            return await tool_press_key(
                keys=params.get("keys", []),
                target_description=params.get("target_description", description),
                safety_tier=safety_tier,
                explanation=description,
            )

        elif action_type == "scroll_screen":
            return await tool_scroll_screen(
                direction=params.get("direction", "down"),
                explanation=description,
                amount=params.get("amount", 3),
            )

        elif action_type == "highlight_area":
            return await tool_highlight_area(
                x=params.get("x", 0),
                y=params.get("y", 0),
                width=params.get("width", 100),
                height=params.get("height", 100),
                explanation=description,
            )

        else:
            logger.warning("Unknown action type: %s", action_type)
            return {
                "status": "error",
                "reason": f"Unknown action type: {action_type}",
            }

    # ── User Confirmation Handlers ─────────────────────────────────────

    async def _handle_user_confirmed(self, payload: dict) -> None:
        """Execute a CLI command the user has confirmed."""
        command = payload.get("command", "")
        explanation = payload.get("explanation", "")

        if not command:
            return

        await self._bus.emit(OdusEvent(EventType.EXECUTION_STARTED))

        result = tool_run_command(command, 2, explanation)

        await self._bus.emit(
            OdusEvent(EventType.EXECUTION_DONE, {
                "summary": f"Executed: {command}",
                "explanation": explanation,
                "result": result,
            })
        )

    async def _handle_input_action_confirmed(self, payload: dict) -> None:
        """Execute a desktop action the user has confirmed."""
        action = payload.get("action", {})
        action_type = action.get("action_type", "")
        explanation = action.get("explanation", "")

        logger.info("User confirmed input action: %s", action_type)

        await self._bus.emit(
            OdusEvent(EventType.INPUT_ACTION_EXECUTING, {
                "action_type": action_type,
                "description": explanation,
            })
        )

        try:
            result = await self._execute_confirmed_input(action)

            await self._bus.emit(
                OdusEvent(EventType.INPUT_ACTION_DONE, {
                    "action_type": action_type,
                    "result": result,
                })
            )

            # If there are remaining plan steps, continue executing them
            remaining = payload.get("remaining_plan", [])
            if remaining:
                logger.info("Resuming plan: %d steps remaining", len(remaining))
                # We'd need the original analysis context here — for now emit status
                await self._bus.emit(
                    OdusEvent(EventType.STATUS_UPDATE, {
                        "message": f"✅ Action completed. {len(remaining)} steps remaining.",
                    })
                )

        except Exception as e:
            logger.error("Input action execution failed: %s", e, exc_info=True)
            await self._bus.emit(
                OdusEvent(EventType.INPUT_ACTION_FAILED, {
                    "action_type": action_type,
                    "reason": str(e),
                })
            )

    async def _execute_confirmed_input(self, action: dict) -> dict:
        """Execute a confirmed input action by dispatching to the simulator."""
        from odus.action.input_sim import get_input_simulator

        sim = get_input_simulator()
        action_type = action.get("action_type", "")

        if action_type == "move_and_click":
            click_type = action.get("click_type", "single")
            button = action.get("button", "left")
            x, y = action.get("x", 0), action.get("y", 0)
            if click_type == "double":
                result = await sim.double_click(x, y)
            elif button == "right":
                result = await sim.right_click(x, y)
            else:
                result = await sim.click(x, y, button=button)

        elif action_type == "type_text":
            result = await sim.type_text(action.get("text", ""))

        elif action_type == "press_key":
            keys = action.get("keys", [])
            if len(keys) == 1:
                result = await sim.press_key(keys[0])
            else:
                result = await sim.hotkey(*keys)

        elif action_type == "scroll_screen":
            result = await sim.scroll(
                action.get("direction", "down"),
                action.get("amount", 3),
            )

        else:
            raise ValueError(f"Cannot execute confirmed action of type: {action_type}")

        return {
            "status": "executed" if result.success else "failed",
            "description": result.description,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

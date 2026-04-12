"""
Agentic Loop — Core event orchestration and analysis routing.
"""

from __future__ import annotations

import asyncio
import logging
import time

from odus.events import EventType, OdusEvent, get_event_bus
from odus.perception.capture import ScreenCapture
from odus.reasoning.tools import (
    tool_run_command,
    get_browser,
)
from odus.reasoning.vision import VisionAnalyzer, AnalysisResult
from odus.reasoning.plan_executor import PlanExecutor

logger = logging.getLogger(__name__)

# Minimum seconds between captures
_CAPTURE_COOLDOWN = 3.0

class Agent:
    """
    The Odus agentic loop. Orchestrates capture, vision, and plan execution.
    """

    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._vision = VisionAnalyzer()
        self._capture = ScreenCapture()
        self._executor = PlanExecutor()
        self._running = False
        self._capturing = False
        self._last_capture_time = 0.0

        logger.info("Agent initialized")

    async def start(self) -> None:
        """Start the agentic loop."""
        self._running = True

        try:
            await self._capture.initialize()
        except Exception as e:
            logger.warning("Capture initialization warning: %s", e)

        listener = self._bus.listen()
        logger.info("Agent loop started — waiting for events...")

        async for event in listener:
            if not self._running: break

            if event.type == EventType.CAPTURE_STARTED:
                query = event.payload.get("query", "") if event.payload else ""
                await self._handle_capture(query)

            elif event.type == EventType.USER_CONFIRMED:
                await self._handle_user_confirmed(event.payload)

            elif event.type == EventType.INPUT_ACTION_CONFIRMED:
                await self._handle_input_action_confirmed(event.payload)

            elif event.type == EventType.PERMISSION_GRANTED:
                await self._handle_permission_granted(event.payload)

            elif event.type == EventType.PERMISSION_DENIED:
                self._executor.paused_context = None

            elif event.type == EventType.AGENT_PLAN_CONFIRMED:
                await self._handle_plan_confirmed(event.payload)

    async def stop(self) -> None:
        self._running = False
        logger.info("Agent loop stopped")

    async def _handle_capture(self, query: str = "") -> None:
        if self._capturing: return
        now = time.monotonic()
        if now - self._last_capture_time < _CAPTURE_COOLDOWN: return

        self._capturing = True
        self._last_capture_time = now

        try:
            # Hide the Odus window so the AI doesn't see its own UI
            await self._bus.emit(OdusEvent(EventType.WINDOW_HIDE_FOR_CAPTURE))
            await asyncio.sleep(0.5)  # Let the compositor process the hide

            logger.info("📸 Capturing screen...")
            result = await self._capture.grab_full_screen()
            compressed, ai_w, ai_h = self._capture.compress(result.png_bytes)

            # Restore the Odus window immediately after capture
            await self._bus.emit(OdusEvent(EventType.WINDOW_SHOW_AFTER_CAPTURE))

            await self._bus.emit(OdusEvent(EventType.CAPTURE_DONE, {
                "width": result.width, "height": result.height, "size_bytes": len(compressed),
            }))

            await self._bus.emit(OdusEvent(EventType.ANALYSIS_STARTED))
            logger.info("🧠 Analyzing with Gemini Vision...")
            analysis = await self._vision.analyze(
                compressed, 
                user_context=query,
                image_width=ai_w,
                image_height=ai_h
            )

            # 📏 Scale coordinates back to native resolution
            self._scale_coordinates(analysis, ai_w, ai_h, result.width, result.height)

            await self._process_analysis(analysis)

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            # Always restore the window even on failure
            await self._bus.emit(OdusEvent(EventType.WINDOW_SHOW_AFTER_CAPTURE))
            await self._bus.emit(OdusEvent(EventType.ERROR, {"message": str(e)}))
        finally:
            self._capturing = False

    def _scale_coordinates(self, analysis: AnalysisResult, ai_w: int, ai_h: int, orig_w: int, orig_h: int) -> None:
        """Scales coordinates from AI resolution back to native screen resolution."""
        if ai_w == orig_w and ai_h == orig_h:
            return

        scale_x = orig_w / ai_w
        scale_y = orig_h / ai_h
        
        logger.debug("Scaling AI coordinates (%dx%d -> %dx%d): x%.2f, y%.2f", 
                     ai_w, ai_h, orig_w, orig_h, scale_x, scale_y)

        for step in analysis.plan:
            params = step.get("params", {})
            orig_params = params.copy()
            modified = False

            if "x" in params and params["x"] is not None:
                params["x"] = round(params["x"] * scale_x)
                modified = True
            if "y" in params and params["y"] is not None:
                params["y"] = round(params["y"] * scale_y)
                modified = True
            if "width" in params and params["width"] is not None:
                params["width"] = round(params["width"] * scale_x)
                modified = True
            if "height" in params and params["height"] is not None:
                params["height"] = round(params["height"] * scale_y)
                modified = True
            
            if modified:
                logger.info(
                    "📍 Scaled step %d coords (Scale: %.2f, %.2f): (%s, %s) -> (%s, %s)", 
                    step.get('step'),
                    scale_x, scale_y,
                    orig_params.get('x'), orig_params.get('y'),
                    params.get('x'), params.get('y')
                )

    async def _process_analysis(self, analysis: AnalysisResult) -> None:
        if analysis.plan:
            await self._executor.process_plan(analysis)
            return

        if not analysis.suggested_commands:
            await self._bus.emit(OdusEvent(EventType.ANALYSIS_DONE, {
                "summary": analysis.summary,
                "explanation": analysis.explanation_for_user,
                "commands": [], "confidence": analysis.confidence,
                "follow_up": analysis.follow_up_hint,
            }))
            return

        # Legacy command handling (Tier 1/2/3)
        for cmd in analysis.suggested_commands:
            if cmd.safety_tier == 1:
                await self._bus.emit(OdusEvent(EventType.EXECUTION_STARTED))
                result = await tool_run_command(cmd.command, cmd.safety_tier, cmd.description)
                await self._bus.emit(OdusEvent(EventType.EXECUTION_DONE, {
                    "summary": analysis.summary, "explanation": analysis.explanation_for_user,
                    "result": result, "confidence": analysis.confidence,
                }))
            elif cmd.safety_tier == 2:
                await self._bus.emit(OdusEvent(EventType.CONFIRM_REQUIRED, {
                    "summary": analysis.summary, "explanation": analysis.explanation_for_user,
                    "command": cmd.command, "description": cmd.description,
                    "safety_tier": cmd.safety_tier, "confidence": analysis.confidence,
                }))
            else:
                await self._bus.emit(OdusEvent(EventType.ANALYSIS_DONE, {
                    "summary": analysis.summary, "explanation": analysis.explanation_for_user,
                    "commands": [], "confidence": analysis.confidence,
                    "warning": f"⚠️ Command '{cmd.command}' was DANGEROUS and blocked.",
                }))

    async def _handle_user_confirmed(self, payload: dict) -> None:
        command, explanation = payload.get("command", ""), payload.get("explanation", "")
        if not command: return
        await self._bus.emit(OdusEvent(EventType.EXECUTION_STARTED))
        result = await tool_run_command(command, 2, explanation)
        await self._bus.emit(OdusEvent(EventType.EXECUTION_DONE, {
            "summary": f"Executed: {command}", "explanation": explanation, "result": result,
        }))

    async def _handle_input_action_confirmed(self, payload: dict) -> None:
        action = payload.get("action", payload)
        action_type = action.get("action_type", "")
        explanation = action.get("explanation", "")

        if not action_type and action.get("command"):
            action_type = "run_command"
            action["action_type"] = "run_command"

        logger.info("User confirmed action: %s", action_type)
        # Note: PlanExecutor already emits EXECUTING if this is part of a plan.
        # Direct confirmation still needs it.
        if not self._executor.paused_context:
            await self._bus.emit(OdusEvent(EventType.INPUT_ACTION_EXECUTING, {
                "action_type": action_type,
                "description": explanation,
                "x": action.get("x"),
                "y": action.get("y"),
            }))
            await asyncio.sleep(0.4)

        try:
            result = await self._executor.execute_confirmed_input(action)
            await self._bus.emit(OdusEvent(EventType.INPUT_ACTION_DONE, {
                "action_type": action_type, "result": result,
            }))

            if self._executor.paused_context:
                ctx = self._executor.paused_context
                self._executor.paused_context = None
                remaining = ctx["plan"][ctx["step_index"]:]
                if remaining:
                    logger.info("Resuming plan from step %d", ctx["step_index"] + 1)
                    await self._executor.process_plan(self._mock_analysis(ctx, remaining))
                else:
                    await self._bus.emit(OdusEvent(EventType.AGENT_PLAN_DONE, {"total_steps": len(ctx['plan'])}))
        except Exception as e:
            logger.error("Execution failed: %s", e, exc_info=True)
            await self._bus.emit(OdusEvent(EventType.INPUT_ACTION_FAILED, {"action_type": action_type, "reason": str(e)}))

    async def _handle_permission_granted(self, payload: dict) -> None:
        path = payload.get("path", "")
        if not path: return
        logger.info("Permission granted for: %s", path)
        get_browser().grant_access(path)

        if self._executor.paused_context:
            ctx = self._executor.paused_context
            self._executor.paused_context = None
            remaining = ctx["plan"][ctx["step_index"] - 1:]
            logger.info("Resuming plan from step %d", ctx["step_index"])
            await self._executor.process_plan(self._mock_analysis(ctx, remaining))

    async def _handle_plan_confirmed(self, payload: dict) -> None:
        if self._executor.paused_context and self._executor.paused_context.get("bulk"):
            ctx = self._executor.paused_context
            self._executor.paused_context = None
            logger.info("Plan bulk-authorized.")
            await self._executor.process_plan(ctx["analysis"], bulk_authorized=True)

    def _mock_analysis(self, ctx: dict, plan: list) -> AnalysisResult:
        class MockAnalysis:
            def __init__(self, s, e, p, c):
                self.summary, self.explanation_for_user, self.plan, self.confidence = s, e, p, c
        return MockAnalysis(ctx["analysis"].summary, ctx["analysis"].explanation_for_user, plan, ctx["analysis"].confidence)

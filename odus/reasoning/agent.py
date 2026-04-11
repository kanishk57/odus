"""
Agentic Loop — Observe → Think → Act → Report.

DEV 2 owns this module.

The Agent listens for CAPTURE_DONE events, runs Vision analysis,
decides on actions, and emits results back to the event bus.
"""

from __future__ import annotations

import asyncio
import logging

from odus.events import EventType, OdusEvent, get_event_bus
from odus.perception.capture import ScreenCapture
from odus.reasoning.tools import tool_run_command, tool_explain, tool_suggest_fix
from odus.reasoning.vision import VisionAnalyzer, AnalysisResult

logger = logging.getLogger(__name__)


class Agent:
    """
    The Odus agentic loop.

    Lifecycle:
        1. Listens for CAPTURE_DONE events on the bus.
        2. Sends the image to Gemini Vision for analysis.
        3. Processes the response:
           - Tier 1 commands → auto-execute → emit EXECUTION_DONE
           - Tier 2 commands → emit CONFIRM_REQUIRED
           - Tier 3 commands → blocked, emit ANALYSIS_DONE with warning
           - No commands → emit ANALYSIS_DONE with explanation only
        4. Waits for the next CAPTURE_DONE.
    """

    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._vision = VisionAnalyzer()
        self._capture = ScreenCapture()
        self._running = False

        logger.info("Agent initialized")

    async def start(self) -> None:
        """Start the agentic loop. Runs until stop() is called."""
        self._running = True
        listener = self._bus.listen()

        logger.info("Agent loop started — waiting for events...")

        async for event in listener:
            if not self._running:
                break

            if event.type == EventType.CAPTURE_STARTED:
                await self._handle_capture()

            elif event.type == EventType.USER_CONFIRMED:
                await self._handle_user_confirmed(event.payload)

    async def stop(self) -> None:
        """Stop the agentic loop."""
        self._running = False
        logger.info("Agent loop stopped")

    async def _handle_capture(self) -> None:
        """Full capture → analyze → act pipeline."""
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

            analysis = await self._vision.analyze(compressed)

            # 3. DECIDE & ACT
            await self._process_analysis(analysis)

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            await self._bus.emit(
                OdusEvent(EventType.ERROR, {"message": str(e)})
            )

    async def _process_analysis(self, analysis: AnalysisResult) -> None:
        """Route the analysis result to the appropriate action."""
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

    async def _handle_user_confirmed(self, payload: dict) -> None:
        """Execute a command the user has confirmed."""
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

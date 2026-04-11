"""
Plan Executor — Logic for step-by-step execution, pausing, and resumption.
"""

from __future__ import annotations

import asyncio
import logging

from odus.events import EventType, OdusEvent, get_event_bus
from odus.reasoning.tools import (
    tool_run_command,
    tool_list_directory,
    tool_read_file,
    tool_explain,
    tool_suggest_fix,
    tool_move_and_click,
    tool_type_text,
    tool_press_key,
    tool_scroll_screen,
    tool_highlight_area,
)
from odus.reasoning.vision import AnalysisResult

logger = logging.getLogger(__name__)

# Desktop control tool names
_INPUT_TOOLS = frozenset({
    "move_and_click", "type_text", "press_key",
    "scroll_screen", "highlight_area",
})

class PlanExecutor:
    """
    Manages the execution state of a multi-step agent plan.
    Handles user confirmations and authorized bypasses.
    """

    def __init__(self):
        self._bus = get_event_bus()
        self._paused_context: dict | None = None

    @property
    def paused_context(self) -> dict | None:
        return self._paused_context

    @paused_context.setter
    def paused_context(self, value: dict | None):
        self._paused_context = value

    async def process_plan(self, analysis: AnalysisResult, bulk_authorized: bool = False) -> None:
        """Execute a multi-step action plan."""
        plan = analysis.plan
        total_steps = len(plan)

        # Check if any step needs confirmation (Tier 2+)
        needs_bulk_auth = any(step.get("safety_tier", 1) >= 2 for step in plan)

        # Emit the full plan to the UI (only on first pass)
        if not bulk_authorized:
            await self._bus.emit(
                OdusEvent(EventType.AGENT_PLAN_CREATED, {
                    "summary": analysis.summary,
                    "explanation": analysis.explanation_for_user,
                    "plan": plan,
                    "total_steps": total_steps,
                    "confidence": analysis.confidence,
                    "needs_confirmation": needs_bulk_auth,
                })
            )

        # If it needs bulk auth and we don't have it yet, pause.
        if needs_bulk_auth and not bulk_authorized:
            self._paused_context = {
                "analysis": analysis,
                "plan": plan,
                "bulk": True,
            }
            logger.info("Plan requires bulk authorization before starting.")
            return

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

            # 👻 Notify UI about desktop actions to trigger Ghost Mode/Cursor
            if action_type in _INPUT_TOOLS:
                await self._bus.emit(OdusEvent(EventType.INPUT_ACTION_EXECUTING, {
                    "action_type": action_type,
                    "description": description,
                    "x": params.get("x"),
                    "y": params.get("y"),
                }))
                # 🐢 Debug Slowdown: Give the user plenty of time to see the Ghost Cursor
                await asyncio.sleep(2.0)

            try:
                result = await self._execute_step(
                    action_type, params, safety_tier, description,
                    authorized=bulk_authorized
                )

                if action_type in _INPUT_TOOLS:
                    await self._bus.emit(OdusEvent(EventType.INPUT_ACTION_DONE, {
                        "action_type": action_type,
                        "result": result,
                    }))

                # 🐢 Debug Slowdown: Long pause after every step
                await asyncio.sleep(2.0)

                # Wait for confirmation if needed
                if result and result.get("status") == "needs_confirmation":
                    self._paused_context = {
                        "analysis": analysis,
                        "step_index": i,
                        "plan": plan,
                    }
                    await self._bus.emit(
                        OdusEvent(EventType.INPUT_ACTION_PLANNED, {
                            "step": i,
                            "total_steps": total_steps,
                            "action": result,
                            "remaining_plan": plan[i:],
                        })
                    )
                    return

                # Wait for permission if needed
                if result and result.get("status") == "needs_permission":
                    self._paused_context = {
                        "analysis": analysis,
                        "step_index": i,
                        "plan": plan,
                    }
                    await self._bus.emit(
                        OdusEvent(EventType.PERMISSION_REQUESTED, {
                            "step": i,
                            "total_steps": total_steps,
                            "resource_type": result.get("resource_type"),
                            "path": result.get("path"),
                            "description": result.get("description"),
                        })
                    )
                    return

                if result and result.get("status") == "blocked":
                    await self._bus.emit(
                        OdusEvent(EventType.INPUT_ACTION_FAILED, {
                            "step": i,
                            "total_steps": total_steps,
                            "reason": result.get("reason", "Action blocked by safety gate."),
                        })
                    )
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

                if i < total_steps and action_type in _INPUT_TOOLS:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error("Step %d/%d failed: %s", i, total_steps, e, exc_info=True)
                if action_type in _INPUT_TOOLS:
                    await self._bus.emit(
                        OdusEvent(EventType.INPUT_ACTION_FAILED, {
                            "action_type": action_type,
                            "reason": str(e),
                        })
                    )
                await self._bus.emit(
                    OdusEvent(EventType.INPUT_ACTION_FAILED, {
                        "step": i,
                        "total_steps": total_steps,
                        "reason": str(e),
                    })
                )
                return

        # All finished
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
        authorized: bool = False,
    ) -> dict:
        """Route a single plan step to the correct tool."""
        if action_type == "run_command":
            return await tool_run_command(params.get("command", ""), safety_tier, description, bypass_confirmation=authorized)
        elif action_type == "list_directory":
            return await tool_list_directory(params.get("path", "."), description)
        elif action_type == "read_file":
            return await tool_read_file(params.get("path", ""), description)
        elif action_type == "explain":
            return tool_explain(params.get("topic", ""), description)
        elif action_type == "suggest_fix":
            return tool_suggest_fix(
                command=params.get("command", ""),
                safety_tier=safety_tier,
                explanation=description,
                risk_warning=params.get("risk_warning", ""),
                x=params.get("x"),
                y=params.get("y")
            )
        elif action_type == "move_and_click":
            return await tool_move_and_click(
                x=params.get("x", 0), y=params.get("y", 0),
                target_description=params.get("target_description", description),
                safety_tier=safety_tier, explanation=description,
                button=params.get("button", "left"), click_type=params.get("click_type", "single"),
                bypass_confirmation=authorized
            )
        elif action_type == "type_text":
            return await tool_type_text(
                params.get("text", ""),
                params.get("target_description", description),
                safety_tier,
                description,
                bypass_confirmation=authorized,
                x=params.get("x"),
                y=params.get("y")
            )
        elif action_type == "press_key":
            return await tool_press_key(
                params.get("keys", []),
                params.get("target_description", description),
                safety_tier,
                description,
                bypass_confirmation=authorized,
                x=params.get("x"),
                y=params.get("y")
            )
        elif action_type == "scroll_screen":
            return await tool_scroll_screen(params.get("direction", "down"), description, params.get("amount", 3))
        elif action_type == "highlight_area":
            return await tool_highlight_area(params.get("x", 0), params.get("y", 0), params.get("width", 100), params.get("height", 100), description)
        else:
            logger.warning("Unknown action type: %s", action_type)
            return {"status": "error", "reason": f"Unknown action type: {action_type}"}

    async def execute_confirmed_input(self, action: dict) -> dict:
        """Execute a confirmed input action by dispatching to the simulator."""
        from odus.action.input_sim import get_input_simulator
        sim = get_input_simulator()
        action_type = action.get("action_type", "")

        if action_type == "move_and_click":
            click_type, button = action.get("click_type", "single"), action.get("button", "left")
            x, y = action.get("x", 0), action.get("y", 0)
            if click_type == "double": result = await sim.double_click(x, y)
            elif button == "right": result = await sim.right_click(x, y)
            else: result = await sim.click(x, y, button=button)
        elif action_type == "type_text":
            result = await sim.type_text(action.get("text", ""), x=action.get("x"), y=action.get("y"))
        elif action_type == "press_key":
            keys = action.get("keys", [])
            if len(keys) == 1:
                result = await sim.press_key(keys[0], x=action.get("x"), y=action.get("y"))
            else:
                result = await sim.hotkey(keys, x=action.get("x"), y=action.get("y"))
        elif action_type == "scroll_screen":
            result = await sim.scroll(action.get("direction", "down"), action.get("amount", 3))
        elif action_type == "run_command":
            await self._bus.emit(OdusEvent(EventType.EXECUTION_STARTED))
            result_dict = await tool_run_command(action.get("command", ""), 1, action.get("explanation", ""))
            return result_dict
        else:
            raise ValueError(f"Cannot execute confirmed action of type: '{action_type}'")

        return {
            "status": "executed" if result.success else "failed",
            "description": result.description,
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

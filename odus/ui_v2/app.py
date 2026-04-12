"""
PyQt6 Application Shell (v2) — wires the sidebar window and event bus.
"""

from __future__ import annotations

import asyncio
import logging
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QObject

from odus.events import EventType, OdusEvent, get_event_bus
from odus.ui_v2.sidebar_window import SidebarWindowV2
from odus.ui_v2.chat_window import ChatWindowV2
from odus.ui_v2.theme import Colors
from odus.ui.overlay import ActionOverlay

logger = logging.getLogger(__name__)

class OdusAppV2(QObject):
    """
    Wires the UI (Sidebar or Window) and event bus together.
    """

    def __init__(self, ui_type: str = "sidebar") -> None:
        super().__init__()
        self._bus = get_event_bus()
        self._ui_type = ui_type

        # ── Main Window ──
        if ui_type == "window":
            self._window = ChatWindowV2()
        else:
            self._window = SidebarWindowV2()

        # ── Action Overlay ──
        self._overlay = ActionOverlay()

        # ── Wire Signals ──

        # Mascot click (in sidebar header)
        self._window.header.mascot_clicked.connect(self._on_mascot_clicked)
        
        # Chat input
        self._window.input_bar.submitted.connect(self._on_user_query)

        # Permission confirmations from inline cards
        self._window.chat_history.action_confirmed.connect(self._on_action_confirmed)
        self._window.chat_history.plan_confirmed.connect(self._on_plan_confirmed)

        # Terminal CWD
        self._window.terminal.set_cwd(os.getcwd())

    def start(self) -> None:
        """Launch the sidebar and hook into asyncio bus."""
        self._window.show()

        # Welcome
        self._window.chat_history.add_message("Hey there! I'm Odus 🦉 — your Linux mentor. How can I help you today?", is_ai=True)
        self._window.chat_history.add_system_log("Ready — press Ctrl+Shift+O to capture.")

        asyncio.create_task(self._event_loop())

    # ── Event Emitters ─────────────────────────────────────────────────

    def _on_mascot_clicked(self) -> None:
        logger.info("Mascot clicked — triggering capture")
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED))
        )

    def _on_plan_confirmed(self) -> None:
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.AGENT_PLAN_CONFIRMED))
        )

    def _on_user_query(self, query: str) -> None:
        logger.info("User submitted query: %s", query)
        self._window.chat_history.add_message(query, is_ai=False)
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED, {"query": query}))
        )

    def _on_action_confirmed(self, action_data: dict) -> None:
        # Hide overlay before executing
        self._overlay.hide()
        
        if action_data.get("resource_type") == "directory":
            asyncio.ensure_future(
                self._bus.emit(OdusEvent(EventType.PERMISSION_GRANTED, action_data))
            )
        elif action_data.get("command"):
            asyncio.ensure_future(
                self._bus.emit(OdusEvent(EventType.USER_CONFIRMED, action_data))
            )
        else:
            asyncio.ensure_future(
                self._bus.emit(OdusEvent(EventType.INPUT_ACTION_CONFIRMED, action_data))
            )

    # ── Event Loop ─────────────────────────────────────────────────────

    async def _event_loop(self) -> None:
        self._handlers = {
            EventType.CAPTURE_STARTED: self._on_capture_started,
            EventType.CAPTURE_DONE: self._on_capture_done,
            EventType.ANALYSIS_STARTED: self._on_analysis_started,
            EventType.ANALYSIS_DONE: self._on_analysis_done,
            EventType.CONFIRM_REQUIRED: self._on_confirm_required,
            EventType.EXECUTION_STARTED: self._on_execution_started,
            EventType.EXECUTION_DONE: self._on_execution_done,
            EventType.AGENT_PLAN_CREATED: self._on_agent_plan_created,
            EventType.AGENT_PLAN_CONFIRMED: self._on_agent_plan_confirmed,
            EventType.AGENT_STEP_STARTED: self._on_agent_step_started,
            EventType.AGENT_STEP_DONE: self._on_agent_step_done,
            EventType.AGENT_PLAN_DONE: self._on_agent_plan_done,
            EventType.INPUT_ACTION_PLANNED: self._on_input_action_planned,
            EventType.INPUT_ACTION_EXECUTING: self._on_input_action_executing,
            EventType.INPUT_ACTION_DONE: self._on_input_action_done,
            EventType.INPUT_ACTION_FAILED: self._on_input_action_failed,
            EventType.PERMISSION_REQUESTED: self._on_permission_requested,
            EventType.PERMISSION_GRANTED: self._on_permission_granted,
            EventType.PERMISSION_DENIED: self._on_permission_denied,
            EventType.TERMINAL_OUTPUT_LINE: self._on_terminal_output_line,
            EventType.TERMINAL_COMMAND_STARTED: self._on_terminal_command_started,
            EventType.TERMINAL_COMMAND_DONE: self._on_terminal_command_done,
            EventType.TERMINAL_CWD_CHANGED: self._on_terminal_cwd_changed,
            EventType.WINDOW_HIDE_FOR_CAPTURE: self._on_window_hide_for_capture,
            EventType.WINDOW_SHOW_AFTER_CAPTURE: self._on_window_show_after_capture,
            EventType.ERROR: self._on_error,
            EventType.STATUS_UPDATE: self._on_status_update,
        }
        listener = self._bus.listen()
        async for event in listener:
            try:
                await self._handle_event(event)
            except Exception as e:
                logger.error("UI event handler error: %s", e, exc_info=True)

    async def _handle_event(self, event: OdusEvent) -> None:
        handler = self._handlers.get(event.type)
        if handler:
            await handler(event)

    async def _on_capture_started(self, event: OdusEvent) -> None:
        self._window.set_mascot_state("thinking")
        self._window.chat_history.add_system_log("📸 Capturing screen...")

    async def _on_capture_done(self, event: OdusEvent) -> None:
        size_kb = event.payload.get("size_bytes", 0) / 1024
        self._window.chat_history.add_system_log(
            f"Captured ({event.payload.get('width', '?')}×{event.payload.get('height', '?')}, {size_kb:.0f} KB)",
            color=Colors.SUCCESS,
        )

    async def _on_analysis_started(self, event: OdusEvent) -> None:
        if hasattr(self._window, "expand"):
            self._window.expand()
        else:
            self._window.show()
            self._window.raise_()
        self._window.set_mascot_state("thinking")
        self._window.chat_history.add_system_log("🧠 Analyzing with Gemini...")

    async def _on_analysis_done(self, event: OdusEvent) -> None:
        if hasattr(self._window, "expand"):
            self._window.expand()
        else:
            self._window.show()
            self._window.raise_()
        self._window.set_mascot_state("idle")
        payload = event.payload
        summary = payload.get("summary", "")
        if summary:
            self._window.chat_history.add_message(summary, is_ai=True)
        
        explanation = payload.get("explanation", "")
        if explanation and explanation != summary:
            self._window.chat_history.add_message(explanation, is_ai=True)

        if payload.get("warning"):
            self._window.chat_history.add_system_log(payload["warning"], color=Colors.WARNING)
        if payload.get("follow_up"):
            self._window.chat_history.add_system_log(f"💡 {payload['follow_up']}")

    async def _on_confirm_required(self, event: OdusEvent) -> None:
        payload = event.payload
        command = payload.get("command", "")
        explanation = payload.get("explanation", "")
        tier = payload.get("safety_tier", 2)

        self._window.chat_history.add_permission_card(
            title="Command Execution",
            description=explanation,
            action_data={"command": command, "explanation": explanation},
            tier=tier,
        )

    async def _on_execution_started(self, event: OdusEvent) -> None:
        self._window.terminal.setVisible(True)
        self._window.chat_history.add_system_log("⚡ Executing...")

    async def _on_execution_done(self, event: OdusEvent) -> None:
        result = event.payload.get("result", {})
        status = result.get("status", "unknown")

        if status == "executed":
            rc = result.get("return_code", -1)
            self._window.terminal.setVisible(True)
            if rc == 0:
                self._window.set_mascot_state("success")
                self._window.terminal.add_success("Command succeeded")
            else:
                self._window.set_mascot_state("error")
                self._window.terminal.add_error(f"Exited with code {rc}")

            if result.get("stdout"):
                self._window.terminal.add_output(result["stdout"])
            if result.get("stderr"):
                self._window.terminal.add_error(result["stderr"])

        elif status == "blocked":
            self._window.chat_history.add_system_log(
                f"🚫 {result.get('reason', 'Blocked')}",
                color=Colors.ERROR,
            )

    async def _on_agent_plan_created(self, event: OdusEvent) -> None:
        payload = event.payload
        self._window.chat_history.add_action_plan(
            summary=payload.get("explanation", payload.get("summary", "")),
            steps=payload.get("plan", []),
            needs_confirmation=payload.get("needs_confirmation", False),
        )

    async def _on_agent_plan_confirmed(self, event: OdusEvent) -> None:
        self._window.chat_history.add_system_log("Implementation plan authorized.", color=Colors.SUCCESS)

    async def _on_agent_step_started(self, event: OdusEvent) -> None:
        step = event.payload.get("step", 0)
        self._window.chat_history.update_action_step(step, "running")

    async def _on_agent_step_done(self, event: OdusEvent) -> None:
        step = event.payload.get("step", 0)
        self._window.chat_history.update_action_step(step, "done")

    async def _on_agent_plan_done(self, event: OdusEvent) -> None:
        total = event.payload.get("total_steps", 0)
        self._window.chat_history.add_system_log(f"✅ All {total} steps completed!", color=Colors.SUCCESS)

    async def _on_input_action_planned(self, event: OdusEvent) -> None:
        payload = event.payload
        action = payload.get("action", {})
        action_type = action.get("action_type", "")
        explanation = action.get("explanation", "")

        # Show on overlay
        if action.get("x") is not None and action.get("y") is not None:
            self._overlay.clear()
            self._overlay.add_action_marker(
                action.get("x"), action.get("y"), 
                action.get("width", 20), action.get("height", 20),
                label=action_type
            )
            self._overlay.show()

        self._window.chat_history.add_permission_card(
            title=f"Desktop Action: {action_type}",
            description=explanation,
            action_data=payload,
            tier=2,
        )

    async def _on_input_action_executing(self, event: OdusEvent) -> None:
        description = event.payload.get("description", "Executing...")
        self._window.chat_history.add_system_log(f"🎯 {description}", color=Colors.PRIMARY)
        self._window.hide()
        self._overlay.hide()

    async def _on_input_action_done(self, event: OdusEvent) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        result = event.payload.get("result", {})
        self._window.chat_history.add_system_log(
            f"✅ {result.get('description', 'Done')}",
            color=Colors.SUCCESS,
        )

    async def _on_input_action_failed(self, event: OdusEvent) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        self._window.chat_history.add_system_log(
            f"❌ {event.payload.get('reason', 'Failed')}",
            color=Colors.ERROR,
        )

    async def _on_permission_requested(self, event: OdusEvent) -> None:
        path = event.payload.get("path", "")
        desc = event.payload.get("description", f"Access to {path}")
        self._window.chat_history.add_permission_card(
            title="Directory Access",
            description=desc,
            action_data=event.payload,
            tier=1,
        )

    async def _on_permission_granted(self, event: OdusEvent) -> None:
        path = event.payload.get("path", "")
        self._window.chat_history.add_system_log(f"✅ Access granted: {path}", color=Colors.SUCCESS)

    async def _on_permission_denied(self, event: OdusEvent) -> None:
        path = event.payload.get("path", "")
        self._window.chat_history.add_system_log(f"🚫 Access denied: {path}", color=Colors.ERROR)

    async def _on_terminal_output_line(self, event: OdusEvent) -> None:
        line = event.payload.get("line", "")
        self._window.terminal.setVisible(True)
        self._window.terminal.add_stream_line(line)

    async def _on_terminal_command_started(self, event: OdusEvent) -> None:
        cmd = event.payload.get("command", "")
        self._window.terminal.setVisible(True)
        self._window.terminal.add_command(cmd)

    async def _on_terminal_command_done(self, event: OdusEvent) -> None:
        rc = event.payload.get("exit_code", 0)
        self._window.terminal.setVisible(True)
        if rc == 0:
            self._window.set_mascot_state("success")
            self._window.terminal.add_success("Command finished")
        else:
            self._window.set_mascot_state("error")
            self._window.terminal.add_error(f"Exited with code {rc}")
        
        # Reset to idle after a delay
        asyncio.get_event_loop().call_later(2, lambda: self._window.set_mascot_state("idle"))

    async def _on_terminal_cwd_changed(self, event: OdusEvent) -> None:
        new_cwd = event.payload.get("cwd", "")
        self._window.terminal.set_cwd(new_cwd)

    async def _on_error(self, event: OdusEvent) -> None:
        self._window.chat_history.add_system_log(
            f"Error: {event.payload.get('message', 'Unknown')}",
            color=Colors.ERROR,
        )

    async def _on_status_update(self, event: OdusEvent) -> None:
        self._window.chat_history.add_system_log(event.payload.get("message", ""))

    async def _on_window_hide_for_capture(self, event: OdusEvent) -> None:
        self._window.hide()

    async def _on_window_show_after_capture(self, event: OdusEvent) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

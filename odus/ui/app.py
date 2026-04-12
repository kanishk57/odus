"""
PyQt6 Application Shell — wires the unified window and event bus.

Manages the single OdusMainWindow and routes all events between
the agent, UI, PTY session, and file browser.
"""

from __future__ import annotations

import asyncio
import logging
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QObject

from odus.events import EventType, OdusEvent, get_event_bus
from odus.ui.main_window import OdusMainWindow
from odus.ui.chat_panel import ChatPanel
from odus.ui.ghost_terminal import GhostTerminal
from odus.ui.overlay import ActionOverlay
from odus.ui.mascot import MascotState
from odus.ui.theme import Colors

logger = logging.getLogger(__name__)


class OdusApp(QObject):
    """
    Wires the unified PyQt window and event bus together.
    """

    def __init__(self) -> None:
        super().__init__()
        self._bus = get_event_bus()

        # ── Main Window ──
        self._window = OdusMainWindow()

        # ── Content Tabs ──
        self._chat = ChatPanel()
        self._terminal = GhostTerminal()

        self._window.add_tab("chat", self._chat)
        self._window.add_tab("terminal", self._terminal)
        self._window.switch_tab("chat")

        # ── Action Overlay ──
        self._overlay = ActionOverlay()

        # ── Wire Signals ──

        # Mascot click → capture
        self._window.sidebar.mascot.clicked.connect(self._on_mascot_clicked)

        # Sidebar buttons
        self._window.capture_requested.connect(self._on_capture)
        self._window.browse_requested.connect(self._on_browse)

        # Chat input
        self._window.input_submitted.connect(self._on_user_query)

        # Permission confirmations from inline cards
        self._chat.action_confirmed.connect(self._on_action_confirmed)
        self._chat.plan_confirmed.connect(self._on_plan_confirmed)

        # Terminal CWD
        self._terminal.set_cwd(os.getcwd())

    def start(self) -> None:
        """Launch the window and hook into asyncio bus."""
        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self._window.width()) // 2
            y = (geo.height() - self._window.height()) // 2
            self._window.move(x, y)

        self._window.show()

        # Welcome
        self._chat.add_ai_message("Hey there! I'm Odus 🦉 — your Linux mentor. Tap the owl or press Ctrl+Shift+O to capture your screen, or type a question below.")
        self._chat.add_system_log("Ready — press Ctrl+Shift+O to capture.")

        asyncio.create_task(self._event_loop())

    # ── Event Emitters ─────────────────────────────────────────────────

    def _on_mascot_clicked(self) -> None:
        asyncio.ensure_future(self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED)))

    def _on_capture(self) -> None:
        asyncio.ensure_future(self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED)))

    def _on_browse(self) -> None:
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.PERMISSION_REQUESTED, {
                "resource_type": "directory",
                "path": os.getcwd(),
                "description": "Browse current project directory",
            }))
        )

    def _on_plan_confirmed(self) -> None:
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.AGENT_PLAN_CONFIRMED))
        )

    def _on_user_query(self, query: str) -> None:
        self._chat.add_user_message(query)
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED, {"query": query}))
        )

    def _on_action_confirmed(self, action_data: dict) -> None:
        # Route based on action type
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
        self._window.mascot.set_state(MascotState.THINKING)
        self._window.sidebar.set_status("Capturing...", Colors.ACCENT)
        self._chat.add_system_log("📸 Capturing screen...")

    async def _on_capture_done(self, event: OdusEvent) -> None:
        size_kb = event.payload.get("size_bytes", 0) / 1024
        self._chat.add_system_log(
            f"Captured ({event.payload.get('width', '?')}×{event.payload.get('height', '?')}, {size_kb:.0f} KB)",
            color=Colors.SUCCESS,
        )

    async def _on_analysis_started(self, event: OdusEvent) -> None:
        self._window.sidebar.set_status("Analyzing...", Colors.ACCENT)
        self._chat.add_system_log("🧠 Analyzing with Gemini...")

    async def _on_analysis_done(self, event: OdusEvent) -> None:
        self._window.mascot.set_state(MascotState.SUCCESS)
        self._window.sidebar.set_status("Ready", Colors.TEXT_SECONDARY)
        payload = event.payload

        self._chat.add_ai_message(payload.get("summary", ""))
        explanation = payload.get("explanation", "")
        if explanation and explanation != payload.get("summary", ""):
            self._chat.add_ai_message(explanation)

        if payload.get("warning"):
            self._chat.add_system_log(payload["warning"], color=Colors.WARNING)
        if payload.get("follow_up"):
            self._chat.add_system_log(f"💡 {payload['follow_up']}")

    async def _on_confirm_required(self, event: OdusEvent) -> None:
        self._window.mascot.set_state(MascotState.WARNING)
        self._window.sidebar.set_tier(2)
        payload = event.payload

        command = payload.get("command", "")
        explanation = payload.get("explanation", "")
        tier = payload.get("safety_tier", 2)

        # Inline permission card instead of QMessageBox
        self._chat.add_permission_card(
            title="Command Execution",
            description=explanation,
            action_data={"command": command, "explanation": explanation},
            tier=tier,
        )

    async def _on_execution_started(self, event: OdusEvent) -> None:
        self._window.switch_tab("terminal")
        self._window.sidebar.set_status("Executing...", Colors.ACCENT)
        self._chat.add_system_log("⚡ Executing...")

    async def _on_execution_done(self, event: OdusEvent) -> None:
        result = event.payload.get("result", {})
        status = result.get("status", "unknown")

        if status == "executed":
            rc = result.get("return_code", -1)
            if rc == 0:
                self._window.mascot.set_state(MascotState.SUCCESS)
                self._window.sidebar.set_status("Ready", Colors.TEXT_SECONDARY)
                self._window.sidebar.set_tier(1)
                self._terminal.add_success("Command succeeded")
            else:
                self._window.mascot.set_state(MascotState.ERROR)
                self._window.sidebar.set_status("Error", Colors.DANGER)
                self._terminal.add_error(f"Exited with code {rc}")

            if result.get("stdout"):
                self._terminal.add_output(result["stdout"])
            if result.get("stderr"):
                self._terminal.add_error(result["stderr"])

        elif status == "blocked":
            self._window.mascot.set_state(MascotState.ERROR)
            self._window.sidebar.set_tier(3)
            self._chat.add_system_log(
                f"🚫 {result.get('reason', 'Blocked')}",
                color=Colors.DANGER,
            )

    async def _on_agent_plan_created(self, event: OdusEvent) -> None:
        self._window.mascot.set_state(MascotState.THINKING)
        self._window.sidebar.set_status("Planning...", Colors.ACCENT)
        payload = event.payload
        self._chat.add_action_plan(
            summary=payload.get("explanation", payload.get("summary", "")),
            steps=payload.get("plan", []),
            needs_confirmation=payload.get("needs_confirmation", False),
        )

    async def _on_agent_plan_confirmed(self, event: OdusEvent) -> None:
        self._chat.add_system_log("Implementation plan authorized.", color=Colors.SUCCESS)
        self._window.mascot.set_state(MascotState.THINKING)

    async def _on_agent_step_started(self, event: OdusEvent) -> None:
        step = event.payload.get("step", 0)
        self._chat.update_action_step(step, "running")

    async def _on_agent_step_done(self, event: OdusEvent) -> None:
        step = event.payload.get("step", 0)
        self._chat.update_action_step(step, "done")

    async def _on_agent_plan_done(self, event: OdusEvent) -> None:
        self._window.mascot.set_state(MascotState.SUCCESS)
        self._window.sidebar.set_status("Ready", Colors.TEXT_SECONDARY)
        total = event.payload.get("total_steps", 0)
        self._chat.add_system_log(f"✅ All {total} steps completed!", color=Colors.SUCCESS)
    async def _on_input_action_planned(self, event: OdusEvent) -> None:
        self._window.mascot.set_state(MascotState.WARNING)
        payload = event.payload
        action = payload.get("action", {})
        action_type = action.get("action_type", "")
        explanation = action.get("explanation", "")

        # Show overlay
        if action_type == "move_and_click":
            x, y = action.get("x", 0), action.get("y", 0)
            target = action.get("target_description", "")
            self._overlay.show_crosshair(x, y, label=f"Click: {target}")
        elif action_type == "highlight_area":
            target = action.get("target_description", "")
            self._overlay.show_highlight(
                x=action.get("x", 0), y=action.get("y", 0),
                w=action.get("width", 100), h=action.get("height", 100),
                label=f"Examine: {target}"
            )

        # Inline permission card
        self._chat.add_permission_card(
            title=f"Desktop Action: {action_type}",
            description=explanation,
            action_data=payload,
            tier=2,
        )

    async def _on_input_action_executing(self, event: OdusEvent) -> None:
        action_type = event.payload.get("action_type", "")
        description = event.payload.get("description", "Executing...")
        
        self._chat.add_system_log(
            f"🎯 {description}",
            color=Colors.ACCENT,
        )
        
        # 👻 Ghost Mode: Hide Odus entirely so ydotool clicks reach the real target.
        # WA_TransparentForMouseEvents only blocks Qt input events — ydotool
        # injects through /dev/uinput, which the Wayland compositor still
        # delivers to whatever surface is under the cursor.
        self._window.hide()
        self._overlay.hide()

    async def _on_input_action_done(self, event: OdusEvent) -> None:
        # Restore window from Ghost Mode
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        
        self._overlay.dismiss()
        
        self._window.mascot.set_state(MascotState.SUCCESS)
        result = event.payload.get("result", {})
        self._chat.add_system_log(
            f"✅ {result.get('description', 'Done')}",
            color=Colors.SUCCESS,
        )

    async def _on_input_action_failed(self, event: OdusEvent) -> None:
        # Restore window from Ghost Mode
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        
        self._overlay.dismiss()
        
        self._window.mascot.set_state(MascotState.ERROR)
        self._chat.add_system_log(
            f"❌ {event.payload.get('reason', 'Failed')}",
            color=Colors.DANGER,
        )

    async def _on_permission_requested(self, event: OdusEvent) -> None:
        path = event.payload.get("path", "")
        desc = event.payload.get("description", f"Access to {path}")
        self._chat.add_permission_card(
            title="Directory Access",
            description=desc,
            action_data=event.payload,
            tier=1,
        )

    async def _on_permission_granted(self, event: OdusEvent) -> None:
        path = event.payload.get("path", "")
        self._chat.add_system_log(f"✅ Access granted: {path}", color=Colors.SUCCESS)

    async def _on_permission_denied(self, event: OdusEvent) -> None:
        path = event.payload.get("path", "")
        self._chat.add_system_log(f"🚫 Access denied: {path}", color=Colors.DANGER)

    async def _on_terminal_output_line(self, event: OdusEvent) -> None:
        line = event.payload.get("line", "")
        self._terminal.add_stream_line(line)

    async def _on_terminal_command_started(self, event: OdusEvent) -> None:
        cmd = event.payload.get("command", "")
        self._terminal.add_command(cmd)
        self._window.switch_tab("terminal")

    async def _on_terminal_command_done(self, event: OdusEvent) -> None:
        rc = event.payload.get("exit_code", 0)
        if rc == 0:
            self._terminal.add_success("Command finished")
        else:
            self._terminal.add_error(f"Exited with code {rc}")
        self._terminal.add_divider()

    async def _on_terminal_cwd_changed(self, event: OdusEvent) -> None:
        new_cwd = event.payload.get("cwd", "")
        self._terminal.set_cwd(new_cwd)

    async def _on_error(self, event: OdusEvent) -> None:
        self._window.mascot.set_state(MascotState.ERROR)
        self._window.sidebar.set_status("Error", Colors.DANGER)
        self._chat.add_system_log(
            f"Error: {event.payload.get('message', 'Unknown')}",
            color=Colors.DANGER,
        )

    async def _on_status_update(self, event: OdusEvent) -> None:
        self._chat.add_system_log(event.payload.get("message", ""))

    async def _on_window_hide_for_capture(self, event: OdusEvent) -> None:
        """Hide the Odus window so screen capture doesn't include our own UI."""
        self._window.hide()
        self._overlay.hide()

    async def _on_window_show_after_capture(self, event: OdusEvent) -> None:
        """Restore the Odus window after screen capture is complete."""
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

"""
PyQt6 Application Shell — manages multiple native windows and the event wiring.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QObject

from odus.events import EventType, OdusEvent, get_event_bus
from odus.ui.chat_interface import ChatInterface
from odus.ui.mascot import MascotWindow, MascotState
from odus.ui.theme import Colors

logger = logging.getLogger(__name__)


class OdusApp(QObject):
    """
    Wires the PyQt multiple-window UI and event bus together natively.
    """

    def __init__(self) -> None:
        super().__init__()
        self._bus = get_event_bus()
        self._app = QApplication.instance()
        if not self._app:
            self._app = QApplication(sys.argv)
            
        # 1. Mascot Window (Floats, totally transparent EGL border)
        self._mascot_win = MascotWindow()
        self._mascot_win.clicked.connect(self._on_mascot_clicked)
        
        # In PyQt on Wayland, sometimes Tool hint masks StaysOnTop.
        # We enforce strict StaysOnTop explicitly.
        self._mascot_win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._mascot_win.setWindowFlag(Qt.WindowType.X11BypassWindowManagerHint, True) # Helps bypass strict WM layering
        
        # Force bottom-right starting position
        screen = self._app.primaryScreen().geometry()
        self._mascot_win.move(screen.width() - 150, screen.height() - 200)
        
        # 2. Terminal Window (Isolated standard frameless window)
        self._terminal = ChatInterface()
        self._terminal.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self._terminal.resize(450, 650)
        
        # Mascot Actions
        self._mascot_win.exit_requested.connect(self._app.quit)
        self._mascot_win.toggle_terminal_requested.connect(self._toggle_terminal)
        
        # Chat Actions
        # Connect input_submitted to the event bus for future AI interaction
        self._terminal.input_submitted.connect(self._on_user_query)


    def start(self) -> None:
        """Launch the windows and hook into asyncio bus."""
        self._mascot_win.show()
        
        # Welcome message
        self._terminal.add_ai_message("Welcome to Odus! 🦉")
        self._terminal.add_system_log("Press Ctrl+Shift+O to capture your screen.")
        
        asyncio.create_task(self._event_loop())

    def _on_mascot_clicked(self) -> None:
        """User clicked the Mascot, force a screen capture!"""
        asyncio.ensure_future(self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED)))

    def _on_user_query(self, query: str) -> None:
        """User typed something in the chat pill."""
        # Trigger an analysis with the user's query as context
        asyncio.ensure_future(
            self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED, {"query": query}))
        )


    def _toggle_terminal(self) -> None:
        if self._terminal.isVisible():
            self._terminal.hide()
        else:
            self._show_terminal()

    def _show_terminal(self) -> None:
        """Ensure the terminal is visible, anchored next to the mascot, and on top."""
        # Anchor next to the Mascot
        m_pos = self._mascot_win.pos()
        # Try to place to the left, but clamp to 0
        target_x = max(0, m_pos.x() - self._terminal.width() - 20)
        self._terminal.move(target_x, m_pos.y())
        
        self._terminal.show()
        self._terminal.raise_()
        self._terminal.activateWindow()

    async def _event_loop(self) -> None:
        """Listen for events on the bus."""
        listener = self._bus.listen()
        async for event in listener:
            try:
                await self._handle_event(event)
            except Exception as e:
                logger.error("UI event handler error: %s", e, exc_info=True)

    async def _handle_event(self, event: OdusEvent) -> None:
        if event.type == EventType.CAPTURE_STARTED:
            self._mascot_win.set_state(MascotState.THINKING)
            self._terminal.add_system_log("📸 Capturing screen...")

        elif event.type == EventType.CAPTURE_DONE:
            size_kb = event.payload.get("size_bytes", 0) / 1024
            self._terminal.add_system_log(
                f"Screen captured ({event.payload.get('width', '?')}x"
                f"{event.payload.get('height', '?')}, {size_kb:.0f} KB)",
                color=Colors.SUCCESS
            )

        elif event.type == EventType.ANALYSIS_STARTED:
            self._terminal.add_system_log("🧠 Analyzing with Gemini Vision...")


        elif event.type == EventType.ANALYSIS_DONE:
            self._mascot_win.set_state(MascotState.SUCCESS)
            self._show_terminal()
            payload = event.payload

            # Use AI Bubbles for the primary summary and explanation
            self._terminal.add_ai_message(payload.get('summary', ''))
            self._terminal.add_ai_message(payload.get("explanation", ""))

            if payload.get("warning"):
                self._terminal.add_system_log(payload["warning"], color=Colors.WARNING)
            if payload.get("follow_up"):
                self._terminal.add_system_log(f"💡 {payload['follow_up']}")

        elif event.type == EventType.CONFIRM_REQUIRED:
            self._mascot_win.set_state(MascotState.WARNING)
            self._show_terminal()
            payload = event.payload

            self._terminal.add_system_log(f"⚠️ {payload.get('summary', '')}", color=Colors.WARNING)
            self._terminal.add_ai_message(payload.get("explanation", ""))
            
            command = payload.get("command", "")
            self._terminal.add_system_log(f"$ {command}", color=Colors.ACCENT)
            self._terminal.add_system_log("This command needs your approval.", color=Colors.WARNING)

            # Use non-blocking dialog to avoid nested event loop crashes with qasync.
            # msgBox.exec() starts a nested Qt loop that conflicts with asyncio.
            self._active_msgbox = QMessageBox()
            self._active_msgbox.setWindowTitle("Odus — Action Required")
            self._active_msgbox.setText(f"Odus wants to run:\n\n{command}")
            self._active_msgbox.setInformativeText(payload.get("explanation", ""))
            
            tier = payload.get("safety_tier", 2)
            if tier == 3:
                self._active_msgbox.setIcon(QMessageBox.Icon.Critical)
            elif tier == 2:
                self._active_msgbox.setIcon(QMessageBox.Icon.Warning)
            else:
                self._active_msgbox.setIcon(QMessageBox.Icon.Information)

            self._active_msgbox.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            self._active_msgbox.setDefaultButton(QMessageBox.StandardButton.Cancel)

            def _on_confirm_finished(result):
                if result == QMessageBox.StandardButton.Ok:
                    asyncio.ensure_future(
                        self._bus.emit(
                            OdusEvent(EventType.USER_CONFIRMED, {
                                "command": command,
                                "explanation": payload.get("explanation", ""),
                            })
                        )
                    )
                else:
                    self._terminal.add_system_log("Action cancelled by user.")
                    self._mascot_win.set_state(MascotState.IDLE)
                self._active_msgbox = None

            self._active_msgbox.finished.connect(_on_confirm_finished)
            self._active_msgbox.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            self._active_msgbox.open()  # Non-blocking — no nested event loop


        elif event.type == EventType.EXECUTION_STARTED:
            self._terminal.add_system_log("⚡ Executing command...")

        elif event.type == EventType.EXECUTION_DONE:
            result = event.payload.get("result", {})
            status = result.get("status", "unknown")

            if status == "executed":
                rc = result.get("return_code", -1)
                if rc == 0:
                    self._mascot_win.set_state(MascotState.SUCCESS)
                    self._terminal.add_system_log("Command executed successfully!", color=Colors.SUCCESS)
                else:
                    self._mascot_win.set_state(MascotState.ERROR)
                    self._terminal.add_system_log(f"Command exited with code {rc}", color=Colors.DANGER)

                if result.get("stdout"):
                    self._terminal.add_system_log(result["stdout"], color=Colors.TEXT_SECONDARY)
                if result.get("stderr"):
                    self._terminal.add_system_log(result["stderr"], color=Colors.DANGER)

            elif status == "blocked":
                self._mascot_win.set_state(MascotState.ERROR)
                self._terminal.add_system_log(
                    f"🚫 {result.get('reason', 'Command was blocked.')}",
                    color=Colors.DANGER
                )

        elif event.type == EventType.ERROR:
            self._mascot_win.set_state(MascotState.ERROR)
            self._show_terminal()
            self._terminal.add_system_log(
                f"Error: {event.payload.get('message', 'Unknown error')}",
                color=Colors.DANGER
            )

        elif event.type == EventType.STATUS_UPDATE:
            self._terminal.add_system_log(
                event.payload.get("message", "")
            )


"""
PyQt6 Application Shell — manages multiple native windows and the event wiring.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import qasync

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from odus.events import EventType, OdusEvent, get_event_bus
from odus.ui.ghost_terminal import GhostTerminal
from odus.ui.mascot import MascotWindow, MascotState

logger = logging.getLogger(__name__)


class OdusApp:
    """
    Wires the PyQt multiple-window UI and event bus together natively.
    """

    def __init__(self) -> None:
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
        self._terminal = GhostTerminal()
        self._terminal.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self._terminal.resize(800, 600)
        
        # Hook our Ghost Terminal's clear button to just Hide the Window for UX
        self._terminal.clear_btn.setText("Hide")
        self._terminal.clear_btn.clicked.disconnect()
        self._terminal.clear_btn.clicked.connect(self._terminal.hide)

    def start(self) -> None:
        """Launch the windows and hook into asyncio bus."""
        self._mascot_win.show()
        
        # Welcome message
        self._terminal.add_info("Welcome to Odus! 🦉")
        self._terminal.add_info("Press Ctrl+Shift+O to capture your screen.")
        self._terminal.add_divider()
        
        asyncio.create_task(self._event_loop())

    def _on_mascot_clicked(self) -> None:
        """User clicked the Mascot, force a screen capture!"""
        asyncio.create_task(self._bus.emit(OdusEvent(EventType.CAPTURE_STARTED)))

    def _toggle_terminal(self) -> None:
        if self._terminal.isVisible():
            self._terminal.hide()
        else:
            # Anchor next to the Mascot
            m_pos = self._mascot_win.pos()
            self._terminal.move(max(0, m_pos.x() - self._terminal.width() - 20), m_pos.y())
            self._terminal.show()

    def _show_terminal(self) -> None:
        if not self._terminal.isVisible():
            self._toggle_terminal()

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
            self._terminal.add_info("📸 Capturing screen...")

        elif event.type == EventType.CAPTURE_DONE:
            size_kb = event.payload.get("size_bytes", 0) / 1024
            self._terminal.add_success(
                f"Screen captured ({event.payload.get('width', '?')}x"
                f"{event.payload.get('height', '?')}, {size_kb:.0f} KB)"
            )

        elif event.type == EventType.ANALYSIS_STARTED:
            self._terminal.add_info("🧠 Analyzing with Gemini Vision...")

        elif event.type == EventType.ANALYSIS_DONE:
            self._mascot_win.set_state(MascotState.SUCCESS)
            self._show_terminal()
            payload = event.payload

            self._terminal.add_divider()
            self._terminal.add_success(f"📋 {payload.get('summary', '')}")
            self._terminal.add_info(payload.get("explanation", ""))

            if payload.get("warning"):
                self._terminal.add_warning(payload["warning"])
            if payload.get("follow_up"):
                self._terminal.add_info(f"💡 {payload['follow_up']}")

        elif event.type == EventType.CONFIRM_REQUIRED:
            self._mascot_win.set_state(MascotState.WARNING)
            self._show_terminal()
            payload = event.payload

            self._terminal.add_divider()
            self._terminal.add_warning(f"⚠️ {payload.get('summary', '')}")
            self._terminal.add_info(payload.get("explanation", ""))
            
            command = payload.get("command", "")
            self._terminal.add_command(command)
            self._terminal.add_warning("This command needs your approval.")

            # Display a standard PyQt MessageBox
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Odus — Action Required")
            msgBox.setText(f"Odus wants to run:\n\n{command}")
            msgBox.setInformativeText(payload.get("explanation", ""))
            
            tier = payload.get("safety_tier", 2)
            if tier == 3:
                msgBox.setIcon(QMessageBox.Icon.Critical)
            elif tier == 2:
                msgBox.setIcon(QMessageBox.Icon.Warning)
            else:
                msgBox.setIcon(QMessageBox.Icon.Information)

            msgBox.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            msgBox.setDefaultButton(QMessageBox.StandardButton.Cancel)

            # Block inside async thread?
            # PyQt message boxes normally block the GUI thread.
            # Using qasync, if it blocks, it might block the async loop.
            # So we use .exec() but since we are running within qasync loop, it's safeish,
            # or ideally we'd show it modelessly, but .exec() works in most cases.
            ret = msgBox.exec()

            if ret == QMessageBox.StandardButton.Ok:
                # User confirmed
                await self._bus.emit(
                    OdusEvent(EventType.USER_CONFIRMED, {
                        "command": command,
                        "explanation": payload.get("explanation", ""),
                    })
                )
            else:
                self._terminal.add_info("Action cancelled by user.")
                self._mascot_win.set_state(MascotState.IDLE)


        elif event.type == EventType.EXECUTION_STARTED:
            self._terminal.add_info("⚡ Executing command...")

        elif event.type == EventType.EXECUTION_DONE:
            result = event.payload.get("result", {})
            status = result.get("status", "unknown")

            if status == "executed":
                rc = result.get("return_code", -1)
                if rc == 0:
                    self._mascot_win.set_state(MascotState.SUCCESS)
                    self._terminal.add_success("Command executed successfully!")
                else:
                    self._mascot_win.set_state(MascotState.ERROR)
                    self._terminal.add_error(f"Command exited with code {rc}")

                if result.get("stdout"):
                    self._terminal.add_output(result["stdout"])
                if result.get("stderr"):
                    self._terminal.add_error(result["stderr"])

            elif status == "blocked":
                self._mascot_win.set_state(MascotState.ERROR)
                self._terminal.add_error(
                    f"🚫 {result.get('reason', 'Command was blocked.')}"
                )

            self._terminal.add_divider()

        elif event.type == EventType.ERROR:
            self._mascot_win.set_state(MascotState.ERROR)
            self._show_terminal()
            self._terminal.add_error(
                f"Error: {event.payload.get('message', 'Unknown error')}"
            )

        elif event.type == EventType.STATUS_UPDATE:
            self._terminal.add_info(
                event.payload.get("message", "")
            )

"""
Flet Application Shell — main window layout and event wiring.

DEV 3 owns this module.

Landscape layout:
  ┌─────────────┬──────────────────────────────────┐
  │             │                                  │
  │   Mascot    │        Ghost Terminal             │
  │   Sidebar   │                                  │
  │             │                                  │
  │  [Status]   │  [Command Output / Analysis]     │
  │             │                                  │
  └─────────────┴──────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from odus.events import EventType, OdusEvent, get_event_bus
from odus.ui.components import confirm_dialog
from odus.ui.ghost_terminal import GhostTerminal
from odus.ui.mascot import MascotController, MascotState
from odus.ui.theme import Colors, FontSizes, Fonts, Spacing, Radii, Layout

logger = logging.getLogger(__name__)


class OdusApp:
    """
    The main Flet application.

    Wires the mascot, ghost terminal, and event bus together.
    """

    def __init__(self) -> None:
        self._bus = get_event_bus()
        self._mascot = MascotController()
        self._terminal = GhostTerminal()
        self._page: ft.Page | None = None

    async def start(self, page: ft.Page) -> None:
        """Initialize and render the Flet app."""
        self._page = page

        # ── Window setup ────────────────────────────────────────────
        page.title = "Odus — AI Linux Mentor"
        page.bgcolor = Colors.BG_PRIMARY
        page.padding = 0
        page.spacing = 0
        page.window.width = Layout.WINDOW_DEFAULT_WIDTH
        page.window.height = Layout.WINDOW_DEFAULT_HEIGHT
        page.window.min_width = Layout.WINDOW_MIN_WIDTH
        page.window.min_height = Layout.WINDOW_MIN_HEIGHT
        page.theme_mode = ft.ThemeMode.DARK

        page.fonts = {
            "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            "JetBrains Mono": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap",
        }

        # ── Layout ──────────────────────────────────────────────────

        # Sidebar: mascot + branding
        sidebar = ft.Container(
            content=ft.Column(
                [
                    # Branding header
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Odus",
                                    size=FontSizes.XXL,
                                    color=Colors.ACCENT,
                                    font_family=Fonts.HEADING,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    "AI Linux Mentor",
                                    size=FontSizes.SM,
                                    color=Colors.TEXT_SECONDARY,
                                    font_family=Fonts.BODY,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=2,
                        ),
                        padding=ft.padding.only(top=Spacing.XL, bottom=Spacing.MD),
                    ),
                    ft.Divider(height=1, color=Colors.BORDER),
                    # Mascot
                    ft.Container(
                        content=self._mascot,
                        expand=True,
                    ),
                    ft.Divider(height=1, color=Colors.BORDER),
                    # Hotkey hint
                    ft.Container(
                        content=ft.Text(
                            "⌨ Ctrl+Shift+O to capture",
                            size=FontSizes.XS,
                            color=Colors.TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                            font_family=Fonts.MONO,
                        ),
                        padding=Spacing.MD,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            width=Layout.SIDEBAR_WIDTH,
            bgcolor=Colors.BG_SECONDARY,
            border=ft.border.only(right=ft.BorderSide(1, Colors.BORDER)),
        )

        # Main panel: ghost terminal
        main_panel = ft.Container(
            content=ft.Column(
                [
                    # Header
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    "Analysis Output",
                                    size=FontSizes.LG,
                                    color=Colors.TEXT_PRIMARY,
                                    font_family=Fonts.HEADING,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(expand=True),
                            ],
                        ),
                        padding=ft.padding.symmetric(
                            horizontal=Spacing.LG,
                            vertical=Spacing.MD,
                        ),
                    ),
                    # Terminal
                    ft.Container(
                        content=self._terminal,
                        expand=True,
                        padding=ft.padding.only(
                            left=Spacing.LG,
                            right=Spacing.LG,
                            bottom=Spacing.LG,
                        ),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )

        # Root layout
        page.add(
            ft.Row(
                [sidebar, main_panel],
                spacing=0,
                expand=True,
            )
        )

        # Welcome message
        self._terminal.add_info("Welcome to Odus! 🦉")
        self._terminal.add_info("Press Ctrl+Shift+O to capture your screen.")
        self._terminal.add_divider()

        # Start listening for events
        asyncio.create_task(self._event_loop())

    async def _event_loop(self) -> None:
        """Listen for events on the bus and update the UI accordingly."""
        listener = self._bus.listen()

        async for event in listener:
            try:
                await self._handle_event(event)
            except Exception as e:
                logger.error("UI event handler error: %s", e, exc_info=True)

    async def _handle_event(self, event: OdusEvent) -> None:
        """Route an event to the appropriate UI handler."""

        if event.type == EventType.CAPTURE_STARTED:
            self._mascot.set_state(MascotState.THINKING)
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
            self._mascot.set_state(MascotState.SUCCESS)
            payload = event.payload

            self._terminal.add_divider()
            self._terminal.add_success(f"📋 {payload.get('summary', '')}")
            self._terminal.add_info(payload.get("explanation", ""))

            if payload.get("warning"):
                self._terminal.add_warning(payload["warning"])

            if payload.get("follow_up"):
                self._terminal.add_info(f"💡 {payload['follow_up']}")

        elif event.type == EventType.CONFIRM_REQUIRED:
            self._mascot.set_state(MascotState.WARNING)
            payload = event.payload

            self._terminal.add_divider()
            self._terminal.add_warning(f"⚠️ {payload.get('summary', '')}")
            self._terminal.add_info(payload.get("explanation", ""))
            self._terminal.add_command(payload.get("command", ""))
            self._terminal.add_warning("This command needs your approval.")

            # Show confirmation dialog
            if self._page:
                command = payload.get("command", "")
                explanation = payload.get("explanation", "")
                tier = payload.get("safety_tier", 2)

                async def on_confirm(e):
                    self._page.close(dialog)
                    await self._bus.emit(
                        OdusEvent(EventType.USER_CONFIRMED, {
                            "command": command,
                            "explanation": explanation,
                        })
                    )

                def on_cancel(e):
                    self._page.close(dialog)
                    self._terminal.add_info("Action cancelled by user.")
                    self._mascot.set_state(MascotState.IDLE)

                dialog = confirm_dialog(
                    command=command,
                    explanation=explanation,
                    safety_tier=tier,
                    on_confirm=on_confirm,
                    on_cancel=on_cancel,
                )
                self._page.open(dialog)

        elif event.type == EventType.EXECUTION_STARTED:
            self._terminal.add_info("⚡ Executing command...")

        elif event.type == EventType.EXECUTION_DONE:
            result = event.payload.get("result", {})
            status = result.get("status", "unknown")

            if status == "executed":
                rc = result.get("return_code", -1)
                if rc == 0:
                    self._mascot.set_state(MascotState.SUCCESS)
                    self._terminal.add_success("Command executed successfully!")
                else:
                    self._mascot.set_state(MascotState.ERROR)
                    self._terminal.add_error(f"Command exited with code {rc}")

                if result.get("stdout"):
                    self._terminal.add_output(result["stdout"])
                if result.get("stderr"):
                    self._terminal.add_error(result["stderr"])

            elif status == "blocked":
                self._mascot.set_state(MascotState.ERROR)
                self._terminal.add_error(
                    f"🚫 {result.get('reason', 'Command was blocked.')}"
                )

            self._terminal.add_divider()

        elif event.type == EventType.ERROR:
            self._mascot.set_state(MascotState.ERROR)
            self._terminal.add_error(
                f"Error: {event.payload.get('message', 'Unknown error')}"
            )

        elif event.type == EventType.STATUS_UPDATE:
            self._terminal.add_info(
                event.payload.get("message", "")
            )

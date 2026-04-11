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

        # State
        self._is_expanded = False
        self._mascot.on_click = self._toggle_expanded

        # ── Window setup ────────────────────────────────────────────
        page.title = "Odus Mascot"
        
        # Make the window always on top, but RESTORE frames so the user can drag it
        # Wayland rigidly blocks Flet's transparent frameless implementations.
        page.window.frameless = False
        page.window.title_bar_hidden = False
        page.window.always_on_top = True
        
        # Start in compact widget mode
        page.window.width = Layout.MASCOT_WIDTH + 60
        page.window.height = Layout.MASCOT_HEIGHT + 100
        page.bgcolor = Colors.BG_PRIMARY
        page.window.bgcolor = Colors.BG_PRIMARY
        page.padding = Spacing.MD

        page.theme_mode = ft.ThemeMode.DARK
        page.fonts = {
            "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            "JetBrains Mono": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap",
        }

        # ── Layout ──────────────────────────────────────────────────

        # Terminal container (the modal)
        self._terminal_container = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Analysis Output",
                                size=FontSizes.LG,
                                color=Colors.TEXT_PRIMARY,
                                font_family=Fonts.HEADING,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_color=Colors.TEXT_SECONDARY,
                                on_click=self._toggle_expanded,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1, color=Colors.BORDER),
                    ft.Container(
                        content=self._terminal,
                        expand=True,
                    ),
                ],
                spacing=Spacing.SM,
            ),
            width=Layout.MODAL_WIDTH,
            height=Layout.MODAL_HEIGHT,
            bgcolor=Colors.BG_PRIMARY,
            border_radius=Radii.LG,
            padding=Spacing.LG,
            border=ft.border.all(1, Colors.BORDER),
            shadow=ft.BoxShadow(
                blur_radius=20,
                spread_radius=2,
                color="#80000000",
            ),
            visible=False,
            scale=ft.Scale(scale=0.9),
            animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT_BACK),
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            opacity=0,
        )

        # Root layout: anchor everything to bottom right
        page.add(
            ft.Row(
                [
                    self._terminal_container,
                    ft.Container(content=self._mascot, alignment=ft.Alignment(1, 1)),
                ],
                vertical_alignment=ft.CrossAxisAlignment.END,
                alignment=ft.MainAxisAlignment.END,
                expand=True,
            )
        )

        # Welcome message
        self._terminal.add_info("Welcome to Odus! 🦉")
        self._terminal.add_info("Press Ctrl+Shift+O to capture your screen.")
        self._terminal.add_divider()

        # Start listening for events
        asyncio.create_task(self._event_loop())

    def _toggle_expanded(self, e=None) -> None:
        """Toggle the visibility of the terminal modal."""
        self._is_expanded = not self._is_expanded
        if self._is_expanded:
            # Expand physical window
            self._page.window.width = Layout.WINDOW_MIN_WIDTH
            self._page.window.height = Layout.WINDOW_MIN_HEIGHT
            # Show interior modal
            self._terminal_container.visible = True
            self._terminal_container.opacity = 1
            self._terminal_container.scale = 1
        else:
            # Hide interior modal
            self._terminal_container.opacity = 0
            self._terminal_container.scale = 0.9
            # Hide it fully and shrink window after animation completes
            self._page.run_task(self._hide_container_after_anim)
        self._page.update()

    async def _hide_container_after_anim(self):
        await asyncio.sleep(0.3)
        if not self._is_expanded:
            self._terminal_container.visible = False
            self._page.window.width = Layout.MASCOT_WIDTH + 60
            self._page.window.height = Layout.MASCOT_HEIGHT + 100
            self._page.update()

    def _show_modal(self) -> None:
        """Force show the modal for important events."""
        if not self._is_expanded:
            self._toggle_expanded()

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
            self._show_modal()
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
            self._show_modal()
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

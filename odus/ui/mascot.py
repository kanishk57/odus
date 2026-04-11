"""
Mascot State Machine — controls the mascot's visual state and animations.

DEV 3 owns this module.

States: IDLE → THINKING → SUCCESS / ERROR / WARNING → IDLE
"""

from __future__ import annotations

import logging
from enum import Enum

import flet as ft

from odus.ui.theme import Colors, FontSizes, Spacing, Radii

logger = logging.getLogger(__name__)


class MascotState(Enum):
    """Visual states of the Odus mascot."""

    IDLE = "idle"
    THINKING = "thinking"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


# Mascot emoji representations (to be replaced with actual sprites)
MASCOT_DISPLAY = {
    MascotState.IDLE: "🦉",
    MascotState.THINKING: "🔍",
    MascotState.SUCCESS: "✅",
    MascotState.ERROR: "❌",
    MascotState.WARNING: "⚠️",
}

MASCOT_MESSAGES = {
    MascotState.IDLE: "Ready to help! Press Ctrl+Shift+O to capture.",
    MascotState.THINKING: "Analyzing your screen...",
    MascotState.SUCCESS: "Found a fix!",
    MascotState.ERROR: "Something went wrong.",
    MascotState.WARNING: "This needs your attention.",
}

MASCOT_COLORS = {
    MascotState.IDLE: Colors.TEXT_SECONDARY,
    MascotState.THINKING: Colors.ACCENT,
    MascotState.SUCCESS: Colors.SUCCESS,
    MascotState.ERROR: Colors.DANGER,
    MascotState.WARNING: Colors.WARNING,
}


class MascotController(ft.Column):
    """
    Flet control that displays the mascot with state-driven visuals.

    Usage:
        mascot = MascotController()
        mascot.set_state(MascotState.THINKING)
    """

    def __init__(self, on_click=None) -> None:
        super().__init__()
        self._state = MascotState.IDLE
        self.on_click = on_click

        # Mascot icon (large emoji placeholder — replace with Image later)
        self._icon = ft.Text(
            value=MASCOT_DISPLAY[MascotState.IDLE],
            size=72,
            text_align=ft.TextAlign.CENTER,
        )

        # Status message
        self._message = ft.Text(
            value=MASCOT_MESSAGES[MascotState.IDLE],
            size=FontSizes.SM,
            color=Colors.TEXT_SECONDARY,
            text_align=ft.TextAlign.CENTER,
            width=220,
        )

        # Thinking indicator (animated dots)
        self._progress = ft.ProgressRing(
            width=24,
            height=24,
            stroke_width=2,
            color=Colors.ACCENT,
            visible=False,
        )

        # Wrap in a Container for click and styling
        self._mascot_container = ft.Container(
            content=ft.Column(
                [
                    self._icon,
                    self._progress,
                    self._message,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=Spacing.SM,
            ),
            bgcolor=Colors.BG_SECONDARY,
            border_radius=Radii.LG,
            padding=Spacing.MD,
            border=ft.border.all(1, Colors.BORDER),
            shadow=ft.BoxShadow(
                blur_radius=15,
                spread_radius=1,
                color="#4D000000",
            ),
            on_click=self._on_click_handler,
        )

        # Layout
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.alignment = ft.MainAxisAlignment.CENTER
        self.controls = [self._mascot_container]

    def _on_click_handler(self, e):
        if self.on_click:
            self.on_click(e)

    @property
    def state(self) -> MascotState:
        return self._state

    def set_state(self, state: MascotState) -> None:
        """Transition to a new mascot state."""
        if state == self._state:
            return

        logger.debug("Mascot: %s → %s", self._state.value, state.value)
        self._state = state

        self._icon.value = MASCOT_DISPLAY[state]
        self._message.value = MASCOT_MESSAGES[state]
        self._message.color = MASCOT_COLORS[state]
        self._progress.visible = (state == MascotState.THINKING)
        self._progress.color = MASCOT_COLORS[state]

        self.update()

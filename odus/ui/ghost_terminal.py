"""
Ghost Terminal — scrollable terminal output visualizer.

DEV 3 owns this module.

Displays analysis results, command outputs, and streaming tokens
in a terminal-like panel with syntax highlighting.
"""

from __future__ import annotations

import logging
from datetime import datetime

import flet as ft

from odus.ui.theme import Colors, FontSizes, Fonts, Spacing, Radii

logger = logging.getLogger(__name__)


class GhostTerminal(ft.Container):
    """
    Terminal-like output display for the Odus UI.

    Features:
      - Scrollable output log
      - Color-coded entries (info, success, error, warning, command)
      - Monospace font
      - Auto-scroll to bottom on new content

    Usage:
        terminal = GhostTerminal()
        terminal.add_info("Analyzing screenshot...")
        terminal.add_success("Found a fix!")
        terminal.add_command("sudo apt install vim")
        terminal.add_output("Reading package lists... Done")
        terminal.add_error("Permission denied")
    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[ft.Control] = []

        # The scrollable column of terminal entries
        self._output = ft.Column(
            controls=[],
            scroll=ft.ScrollMode.AUTO,
            spacing=2,
            auto_scroll=True,
        )

        # Terminal header bar
        self._header = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.TERMINAL, size=14, color=Colors.TEXT_SECONDARY),
                    ft.Text(
                        "Ghost Terminal",
                        size=FontSizes.XS,
                        color=Colors.TEXT_SECONDARY,
                        font_family=Fonts.MONO,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Clear",
                        on_click=self._on_clear,
                        style=ft.ButtonStyle(
                            color=Colors.TEXT_SECONDARY,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=Spacing.SM,
            ),
            padding=ft.padding.symmetric(horizontal=Spacing.MD, vertical=Spacing.SM),
            border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
        )

        # Assemble the terminal container
        self.content = ft.Column(
            [self._header, self._output],
            spacing=0,
            expand=True,
        )
        self.bgcolor = Colors.TERMINAL_BG
        self.border_radius = Radii.MD
        self.border = ft.border.all(1, Colors.BORDER)
        self.padding = 0
        self.expand = True

    # ── Public API ──────────────────────────────────────────────────────

    def add_info(self, text: str) -> None:
        """Add an informational message (gray)."""
        self._add_entry(text, Colors.TERMINAL_TEXT, "›")

    def add_success(self, text: str) -> None:
        """Add a success message (green)."""
        self._add_entry(text, Colors.TERMINAL_GREEN, "✓")

    def add_error(self, text: str) -> None:
        """Add an error message (red)."""
        self._add_entry(text, Colors.TERMINAL_RED, "✗")

    def add_warning(self, text: str) -> None:
        """Add a warning message (yellow)."""
        self._add_entry(text, Colors.TERMINAL_YELLOW, "⚠")

    def add_command(self, command: str) -> None:
        """Add a command being executed (blue, bold)."""
        self._add_entry(
            f"$ {command}",
            Colors.TERMINAL_BLUE,
            "▶",
            bold=True,
        )

    def add_output(self, text: str) -> None:
        """Add raw command output (dim)."""
        for line in text.strip().split("\n"):
            self._add_entry(line, Colors.TEXT_SECONDARY, " ")

    def add_divider(self) -> None:
        """Add a visual separator line."""
        self._output.controls.append(
            ft.Container(
                content=ft.Divider(height=1, color=Colors.BORDER),
                padding=ft.padding.symmetric(horizontal=Spacing.MD, vertical=Spacing.XS),
            )
        )
        self._output.update()

    def clear(self) -> None:
        """Clear all terminal output."""
        self._output.controls.clear()
        self._output.update()

    # ── Private ─────────────────────────────────────────────────────────

    def _add_entry(
        self,
        text: str,
        color: str,
        prefix: str = "›",
        bold: bool = False,
    ) -> None:
        """Add a single timestamped entry to the terminal."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        entry = ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        timestamp,
                        size=FontSizes.XS,
                        color=Colors.TEXT_SECONDARY,
                        font_family=Fonts.MONO,
                        opacity=0.5,
                    ),
                    ft.Text(
                        prefix,
                        size=FontSizes.SM,
                        color=color,
                        font_family=Fonts.MONO,
                    ),
                    ft.Text(
                        text,
                        size=FontSizes.SM,
                        color=color,
                        font_family=Fonts.MONO,
                        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
                        selectable=True,
                        expand=True,
                    ),
                ],
                spacing=Spacing.SM,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.symmetric(horizontal=Spacing.MD, vertical=2),
        )

        self._output.controls.append(entry)
        self._output.update()

    def _on_clear(self, e) -> None:
        """Handle clear button click."""
        self.clear()

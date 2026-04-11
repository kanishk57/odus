"""
Reusable UI Components — buttons, dialogs, badges.

DEV 3 owns this module.
"""

from __future__ import annotations

import flet as ft

from odus.ui.theme import Colors, FontSizes, Fonts, Spacing, Radii, Layout


def safety_badge(tier: int) -> ft.Container:
    """Create a colored safety tier badge."""
    color = Layout.TIER_COLORS.get(tier, Colors.TEXT_SECONDARY)
    label = Layout.TIER_LABELS.get(tier, "UNKNOWN")

    return ft.Container(
        content=ft.Text(
            label,
            size=FontSizes.XS,
            color="#ffffff",
            font_family=Fonts.BODY,
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=color,
        border_radius=Radii.SM,
        padding=ft.padding.symmetric(horizontal=Spacing.SM, vertical=2),
    )


def confirm_dialog(
    command: str,
    explanation: str,
    safety_tier: int,
    on_confirm,
    on_cancel,
) -> ft.AlertDialog:
    """
    Create a confirmation dialog for tier-2 commands.

    Shows the command, explanation, safety tier badge, and
    "Fix it!" / "Cancel" buttons.
    """
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=Colors.WARNING, size=24),
                ft.Text(
                    "Confirm Action",
                    size=FontSizes.LG,
                    color=Colors.TEXT_PRIMARY,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=Spacing.SM,
        ),
        content=ft.Column(
            [
                ft.Text(
                    explanation,
                    size=FontSizes.MD,
                    color=Colors.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.MD),
                ft.Text(
                    "Command to execute:",
                    size=FontSizes.SM,
                    color=Colors.TEXT_SECONDARY,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Container(
                    content=ft.Text(
                        f"$ {command}",
                        size=FontSizes.SM,
                        color=Colors.TERMINAL_BLUE,
                        font_family=Fonts.MONO,
                        selectable=True,
                    ),
                    bgcolor=Colors.TERMINAL_BG,
                    border_radius=Radii.SM,
                    padding=Spacing.MD,
                    border=ft.border.all(1, Colors.BORDER),
                ),
                ft.Container(height=Spacing.SM),
                ft.Row([safety_badge(safety_tier)]),
            ],
            tight=True,
            spacing=Spacing.XS,
        ),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=on_cancel,
                style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
            ),
            ft.ElevatedButton(
                "Fix it!",
                on_click=on_confirm,
                color="#ffffff",
                bgcolor=Colors.ACCENT,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=Radii.SM),
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=Colors.BG_ELEVATED,
        shape=ft.RoundedRectangleBorder(radius=Radii.LG),
    )


def status_chip(label: str, color: str, icon: ft.Icons | None = None) -> ft.Container:
    """Create a small status chip for the status bar."""
    controls = []
    if icon:
        controls.append(ft.Icon(icon, size=12, color=color))
    controls.append(
        ft.Text(
            label,
            size=FontSizes.XS,
            color=color,
            font_family=Fonts.BODY,
        )
    )

    return ft.Container(
        content=ft.Row(controls, spacing=4),
        border=ft.border.all(1, color),
        border_radius=Radii.PILL,
        padding=ft.padding.symmetric(horizontal=Spacing.SM, vertical=2),
    )

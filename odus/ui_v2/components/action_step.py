"""
Action Step Widget (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt

from odus.ui_v2.theme import (
    Colors, FontSizes, Fonts, Radii, Spacing
)

_STATUS_ICONS = {
    "pending": "○",
    "running": "◉",
    "done": "✓",
    "failed": "✕",
    "blocked": "⊘",
}

_STATUS_COLORS = {
    "pending": Colors.TEXT_SECONDARY,
    "running": Colors.PRIMARY,
    "done": Colors.SUCCESS,
    "failed": Colors.ERROR,
    "blocked": Colors.ERROR,
}

_ACTION_TYPE_LABELS = {
    "move_and_click": "Click",
    "type_text": "Type",
    "press_key": "Key",
    "scroll_screen": "Scroll",
    "highlight_area": "Look",
    "run_command": "Run",
    "explain": "Learn",
    "suggest_fix": "Fix",
}


class ActionStepWidgetV2(QFrame):
    """A single step in a multi-step action plan."""

    def __init__(self, step_num: int, total: int, action_type: str, description: str):
        super().__init__()
        self._status = "pending"
        self.setObjectName("ActionStep")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Status icon
        self.status_label = QLabel(_STATUS_ICONS["pending"])
        self.status_label.setFixedWidth(16)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")

        # Step counter
        step_label = QLabel(f"{step_num}/{total}")
        step_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.XS}px; font-family: {Fonts.MONO};")
        step_label.setFixedWidth(24)

        # Action badge
        badge_text = _ACTION_TYPE_LABELS.get(action_type, action_type).upper()
        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            color: {Colors.PRIMARY};
            background-color: transparent;
            border: 1px solid {Colors.PRIMARY};
            border-radius: {Radii.SM}px;
            padding: 1px 6px;
            font-size: 10px;
            font-family: '{Fonts.HEADLINE}';
            font-weight: bold;
        """)
        badge.setFixedHeight(18)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-family: '{Fonts.BODY}'; font-size: {FontSizes.SM}px;")

        layout.addWidget(self.status_label)
        layout.addWidget(step_label)
        layout.addWidget(badge)
        layout.addWidget(desc_label, stretch=1)

        self._apply_style()

    def set_status(self, status: str) -> None:
        self._status = status
        icon = _STATUS_ICONS.get(status, "?")
        color = _STATUS_COLORS.get(status, Colors.TEXT_SECONDARY)
        self.status_label.setText(icon)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(f"""
            QFrame#ActionStep {{
                background-color: {Colors.BG_LEVEL_2};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER_GHOST};
                padding: 2px 4px;
            }}
        """)

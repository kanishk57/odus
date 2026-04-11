"""
Action Step Widget — Visual indicator for a single step in an execution plan.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt

from odus.ui.theme import (
    Colors, FontSizes, Fonts, Radii,
)

_STATUS_ICONS = {
    "pending": "○",
    "running": "◉",
    "done": "✓",
    "failed": "✗",
    "blocked": "⊘",
}

_STATUS_COLORS = {
    "pending": Colors.TEXT_DIM,
    "running": Colors.ACCENT,
    "done": Colors.SUCCESS,
    "failed": Colors.DANGER,
    "blocked": Colors.DANGER,
}

_ACTION_TYPE_LABELS = {
    "move_and_click": "🖱 Click",
    "type_text": "⌨ Type",
    "press_key": "⌨ Key",
    "scroll_screen": "↕ Scroll",
    "highlight_area": "🔍 Look",
    "run_command": "⚡ Run",
    "explain": "💡 Learn",
    "suggest_fix": "🔧 Fix",
}


class ActionStepWidget(QFrame):
    """A single step in a multi-step action plan."""

    def __init__(self, step_num: int, total: int, action_type: str, description: str):
        super().__init__()
        self._status = "pending"
        self.setObjectName("ActionStep")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Status icon
        self.status_label = QLabel(_STATUS_ICONS["pending"])
        self.status_label.setFixedWidth(20)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 14px;")

        # Step counter
        step_label = QLabel(f"{step_num}/{total}")
        step_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: {FontSizes.XS}px; font-family: {Fonts.MONO};")
        step_label.setFixedWidth(28)

        # Action badge
        badge_text = _ACTION_TYPE_LABELS.get(action_type, action_type)
        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            color: {Colors.ACCENT};
            background-color: {Colors.ACCENT_GLOW};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: {FontSizes.XS}px;
            font-weight: bold;
        """)
        badge.setFixedHeight(22)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {FontSizes.SM}px;")

        layout.addWidget(self.status_label)
        layout.addWidget(step_label)
        layout.addWidget(badge)
        layout.addWidget(desc_label, stretch=1)

        self._apply_style()

    def set_status(self, status: str) -> None:
        self._status = status
        icon = _STATUS_ICONS.get(status, "?")
        color = _STATUS_COLORS.get(status, Colors.TEXT_DIM)
        self.status_label.setText(icon)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        self._apply_style()

    def _apply_style(self) -> None:
        border_color = _STATUS_COLORS.get(self._status, Colors.BORDER)
        self.setStyleSheet(f"""
            QFrame#ActionStep {{
                background-color: {Colors.BG_SECONDARY};
                border-radius: {Radii.SM}px;
                border-left: 3px solid {border_color};
            }}
        """)

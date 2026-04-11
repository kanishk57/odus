"""
Chat Interface — Obsidian glass chat panel for the unified window.

No longer a standalone window. Lives inside OdusMainWindow's content stack.
Features: AI/user message bubbles, action step widgets, inline permission cards.
"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor

from odus.ui.theme import (
    Colors, FontSizes, Fonts, Radii, Spacing,
    Gradients, Animations, Layout,
)

logger = logging.getLogger(__name__)


# ── Message Bubble ─────────────────────────────────────────────────────

class MessageBubble(QFrame):
    """A stylized message bubble with entrance animation."""

    def __init__(self, text: str, is_ai: bool = True):
        super().__init__()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)
        self._layout.setSpacing(4)

        # Avatar + message row
        if is_ai:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.setAlignment(Qt.AlignmentFlag.AlignTop)

            avatar = QLabel("🦉")
            avatar.setFixedSize(24, 24)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(f"""
                background-color: {Colors.ACCENT_GLOW};
                border-radius: 12px;
                font-size: 14px;
            """)
            row.addWidget(avatar)

            self.label = QLabel(text)
            self.label.setWordWrap(True)
            self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.SM}px;
                line-height: 1.6;
            """)
            row.addWidget(self.label, stretch=1)

            self._layout.addLayout(row)

            self.setObjectName("AiBubble")
            self.setStyleSheet(f"""
                QFrame#AiBubble {{
                    background-color: {Colors.BG_GLASS};
                    border-radius: {Radii.MD}px;
                    border: 1px solid {Colors.BORDER_SUBTLE};
                }}
            """)
        else:
            self.label = QLabel(text)
            self.label.setWordWrap(True)
            self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.label.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.label.setStyleSheet(f"""
                color: {Colors.ACCENT};
                font-size: {FontSizes.SM}px;
                font-weight: bold;
            """)
            self._layout.addWidget(self.label)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignRight)

            self.setObjectName("UserBubble")
            self.setStyleSheet(f"""
                QFrame#UserBubble {{
                    background-color: transparent;
                }}
            """)

        # Entrance animation
        self._animate_entrance()

    def _animate_entrance(self):
        """Fade-in + subtle appearance."""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(Animations.NORMAL)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()


# ── Permission Card ────────────────────────────────────────────────────

class PermissionCard(QFrame):
    """
    Inline permission request card — replaces QMessageBox.

    Shows: icon + description + command preview + Allow/Deny buttons.
    Styled with Obsidian theme, animated entrance.
    """

    allowed = pyqtSignal(dict)
    denied = pyqtSignal()

    def __init__(self, title: str, description: str, action_data: dict, tier: int = 2, parent=None):
        super().__init__(parent)
        self.setObjectName("PermissionCard")
        self._action_data = action_data
        self._tier = tier

        tier_color = {1: Colors.SUCCESS, 2: Colors.WARNING, 3: Colors.DANGER}.get(tier, Colors.WARNING)
        tier_glow = {1: Colors.SUCCESS_GLOW, 2: Colors.WARNING_GLOW, 3: Colors.DANGER_GLOW}.get(tier, Colors.WARNING_GLOW)
        tier_label = {1: "SAFE", 2: "CAUTION", 3: "DANGER"}.get(tier, "CAUTION")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header row: tier badge + title
        header = QHBoxLayout()
        header.setSpacing(10)

        badge = QLabel(f"⚠ {tier_label}")
        badge.setFont(QFont(Fonts.MONO, FontSizes.XS, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            color: {tier_color};
            background-color: {tier_glow};
            border-radius: 8px;
            padding: 2px 10px;
        """)
        badge.setFixedHeight(22)
        header.addWidget(badge)

        title_label = QLabel(title)
        title_label.setFont(QFont(Fonts.BODY, FontSizes.SM, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header.addWidget(title_label, stretch=1)
        layout.addLayout(header)

        # Description
        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.SM}px; line-height: 1.5;")
        layout.addWidget(desc)

        # Command preview (if present)
        command = action_data.get("command", "") or action_data.get("text", "")
        if command:
            cmd_frame = QFrame()
            cmd_frame.setObjectName("CmdPreview")
            cmd_frame.setStyleSheet(f"""
                QFrame#CmdPreview {{
                    background-color: {Colors.TERMINAL_BG};
                    border-radius: {Radii.SM}px;
                    border: 1px solid {Colors.BORDER_SUBTLE};
                    padding: 8px 12px;
                }}
            """)
            cmd_layout = QVBoxLayout(cmd_frame)
            cmd_layout.setContentsMargins(12, 8, 12, 8)
            cmd_label = QLabel(f"$ {command}")
            cmd_label.setFont(QFont(Fonts.MONO, FontSizes.XS))
            cmd_label.setStyleSheet(f"color: {Colors.TERMINAL_BLUE};")
            cmd_label.setWordWrap(True)
            cmd_layout.addWidget(cmd_label)
            layout.addWidget(cmd_frame)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        deny_btn = QPushButton("✕  Deny")
        deny_btn.setFixedHeight(32)
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.setFont(QFont(Fonts.BODY, FontSizes.XS, QFont.Weight.Bold))
        deny_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 16px;
                padding: 4px 20px;
            }}
            QPushButton:hover {{
                color: {Colors.DANGER};
                border-color: {Colors.DANGER};
                background-color: {Colors.DANGER_GLOW};
            }}
        """)

        allow_btn = QPushButton("✓  Allow")
        allow_btn.setFixedHeight(32)
        allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        allow_btn.setFont(QFont(Fonts.BODY, FontSizes.XS, QFont.Weight.Bold))
        allow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: #000000;
                border: none;
                border-radius: 16px;
                padding: 4px 20px;
            }}
            QPushButton:hover {{
                background-color: #2dd870;
            }}
        """)

        deny_btn.clicked.connect(self._on_deny)
        allow_btn.clicked.connect(self._on_allow)

        btn_row.addWidget(deny_btn)
        btn_row.addWidget(allow_btn)
        layout.addLayout(btn_row)

        # Card styling
        self.setStyleSheet(f"""
            QFrame#PermissionCard {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: {Radii.MD}px;
                border-left: 3px solid {tier_color};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-left: 3px solid {tier_color};
            }}
        """)

        # Entrance animation
        self._animate_entrance()

    def _on_allow(self):
        self.setEnabled(False)
        self.setStyleSheet(self.styleSheet() + f"""
            QFrame#PermissionCard {{ opacity: 0.6; }}
        """)
        self.allowed.emit(self._action_data)

    def _on_deny(self):
        self.setEnabled(False)
        self.denied.emit()

    def _animate_entrance(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(Animations.NORMAL)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()


# ── Chat Panel ─────────────────────────────────────────────────────────

class ChatPanel(QWidget):
    """
    The chat content panel — lives inside OdusMainWindow's content stack.
    No window chrome (that's handled by the main window).
    """

    action_confirmed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("tab_name", "chat")

        self._step_widgets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scrollable chat area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; }}
            QScrollBar:vertical {{
                border: none; background: transparent; width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER}; border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(12)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)

        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll)

    # ── Public API ─────────────────────────────────────────────────────

    def add_ai_message(self, text: str):
        if not text:
            return
        bubble = MessageBubble(text, is_ai=True)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_user_message(self, text: str):
        if not text:
            return
        bubble = MessageBubble(text, is_ai=False)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_system_log(self, text: str, color: str = None):
        """Minimalist log entry."""
        if not text:
            return
        log_label = QLabel(f"  › {text}")
        log_label.setWordWrap(True)
        log_label.setStyleSheet(f"""
            color: {color or Colors.TEXT_SECONDARY};
            font-family: {Fonts.MONO};
            font-size: {FontSizes.XS}px;
            padding: 2px 8px;
        """)
        self.chat_layout.addWidget(log_label)
        self._scroll_to_bottom()

    def add_permission_card(
        self,
        title: str,
        description: str,
        action_data: dict,
        tier: int = 2,
    ) -> PermissionCard:
        """Show an inline permission request card."""
        card = PermissionCard(title, description, action_data, tier)
        card.allowed.connect(lambda data: self.action_confirmed.emit(data))
        card.denied.connect(lambda: self.add_system_log("Action denied by user.", color=Colors.DANGER))
        self.chat_layout.addWidget(card)
        self._scroll_to_bottom()
        return card

    def add_action_plan(self, summary: str, steps: list[dict]) -> None:
        """Display a multi-step action plan."""
        self.add_ai_message(summary)
        self._step_widgets = {}
        for step in steps:
            step_num = step.get("step", 0)
            total = len(steps)
            action_type = step.get("action_type", "unknown")
            description = step.get("description", "")
            widget = ActionStepWidget(step_num, total, action_type, description)
            self._step_widgets[step_num] = widget
            self.chat_layout.addWidget(widget)
        self._scroll_to_bottom()

    def update_action_step(self, step_num: int, status: str) -> None:
        widget = self._step_widgets.get(step_num)
        if widget:
            widget.set_status(status)
            self._scroll_to_bottom()

    def clear(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._step_widgets = {}

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))


# ── Action Step Widget ─────────────────────────────────────────────────

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

"""
Chat Interface — Modern Obsidian/Glass chat UI for Odus.
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextEdit, QLineEdit, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from odus.ui.theme import Colors, FontSizes, Fonts, Radii

logger = logging.getLogger(__name__)


class MessageBubble(QFrame):
    """A stylized message bubble with Glassmorphism support."""
    
    def __init__(self, text: str, is_ai: bool = True):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Styles
        if is_ai:
            self.setObjectName("AiBubble")
            bg = Colors.BG_GLASS
            color = Colors.TEXT_PRIMARY
            self.label.setStyleSheet(f"color: {color}; line-height: 1.6;")
        else:
            self.setObjectName("UserBubble")
            bg = "transparent"
            color = Colors.ACCENT
            self.label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.setStyleSheet(f"""
            QFrame#AiBubble {{
                background-color: {bg};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER};
            }}
            QFrame#UserBubble {{
                background-color: {bg};
            }}
        """)
        
        self.layout.addWidget(self.label)


class ChatInterface(QWidget):
    """
    The new primary interaction window for Odus.
    Combines AI chat bubbles with a command input pill.
    """
    
    input_submitted = pyqtSignal(str)
    action_confirmed = pyqtSignal(dict)  # Emitted when user approves a desktop action

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatInterface")
        self.setMinimumSize(400, 600)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # 1. Header
        header = QHBoxLayout()
        title = QLabel("ODUS")
        title.setStyleSheet(f"color: {Colors.ACCENT}; font-weight: bold; letter-spacing: 2px;")
        title.setFont(QFont(Fonts.HEADING, FontSizes.MD))
        header.addWidget(title)
        header.addStretch()

        # Window Controls
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.min_btn = QPushButton("—")
        self.max_btn = QPushButton("□")
        self.close_btn = QPushButton("✕")

        for btn in (self.min_btn, self.max_btn, self.close_btn):
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_SECONDARY};
                    border: none;
                    font-weight: bold;
                    font-size: 14px;
                    border-radius: 14px;
                }}
                QPushButton:hover {{
                    color: {Colors.TEXT_PRIMARY};
                    background-color: {Colors.BG_ELEVATED};
                }}
            """)
            btn_layout.addWidget(btn)

        self.close_btn.setStyleSheet(self.close_btn.styleSheet() + f"""
            QPushButton:hover {{
                color: white;
                background-color: {Colors.DANGER};
            }}
        """)

        self.min_btn.clicked.connect(self.window().showMinimized)
        
        def toggle_maximize():
            if self.window().isMaximized():
                self.window().showNormal()
            else:
                self.window().showMaximized()
                
        self.max_btn.clicked.connect(toggle_maximize)
        self.close_btn.clicked.connect(self.window().hide)

        header.addLayout(btn_layout)

        self.layout.addLayout(header)

        # 2. Chat Area (Scrollable)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(20)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll.setWidget(self.chat_container)
        self.layout.addWidget(self.scroll)

        # 3. Input Pill
        self.input_container = QFrame()
        self.input_container.setObjectName("InputContainer")
        self.input_container.setFixedHeight(50)
        
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(15, 0, 10, 0)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Odus something...")
        self.input_field.setFrame(False)
        self.input_field.setObjectName("CommandInput")
        self.input_field.returnPressed.connect(self._on_submit)
        
        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.clicked.connect(self._on_submit)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        self.layout.addWidget(self.input_container)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QWidget#ChatInterface {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER};
            }}
            QFrame#InputContainer {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 25px;
                border: 1px solid {Colors.BORDER};
            }}
            QLineEdit#CommandInput {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.MD}px;
            }}
            QPushButton#SendBtn {{
                background-color: {Colors.ACCENT};
                color: #000000;
                border-radius: 15px;
                font-weight: bold;
            }}
            QPushButton#SendBtn:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER};
                border-radius: 2px;
            }}
        """)

    def add_ai_message(self, text: str):
        bubble = MessageBubble(text, is_ai=True)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_user_message(self, text: str):
        bubble = MessageBubble(text, is_ai=False)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_system_log(self, text: str, color: str = None):
        """Minimalist log entry for terminal outputs."""
        log_label = QLabel(f"› {text}")
        log_label.setStyleSheet(f"color: {color or Colors.TEXT_SECONDARY}; font-family: {Fonts.MONO}; font-size: {FontSizes.XS}px;")
        log_label.setWordWrap(True)
        self.chat_layout.addWidget(log_label)
        self._scroll_to_bottom()

    def add_action_plan(self, summary: str, steps: list[dict]) -> None:
        """Display a multi-step action plan from the agent."""
        # Plan header
        self.add_ai_message(summary)

        # Render each step
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
        """
        Update a step's visual status.

        Args:
            step_num: Step number (1-indexed).
            status: 'pending', 'running', 'done', 'failed', 'blocked'.
        """
        widget = getattr(self, '_step_widgets', {}).get(step_num)
        if widget:
            widget.set_status(status)
            self._scroll_to_bottom()

    def add_action_confirmation(self, description: str, action_data: dict) -> None:
        """Show an inline approval request for a desktop action."""
        container = QFrame()
        container.setObjectName("ConfirmAction")
        container.setStyleSheet(f"""
            QFrame#ConfirmAction {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: {Radii.MD}px;
                border: 1px solid {Colors.WARNING};
                padding: 8px;
            }}
        """)
        layout = QVBoxLayout(container)
        layout.setSpacing(8)

        desc_label = QLabel(f"⚠️ {description}")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {FontSizes.SM}px;")
        layout.addWidget(desc_label)

        btn_row = QHBoxLayout()
        approve_btn = QPushButton("✓ Approve")
        approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        approve_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: #000000;
                border-radius: 12px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #2dd870; }}
        """)

        reject_btn = QPushButton("✕ Reject")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: #ffffff;
                border-radius: 12px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #ff8898; }}
        """)

        approve_btn.clicked.connect(lambda: self._on_action_confirmed(action_data, container))
        reject_btn.clicked.connect(lambda: self._on_action_rejected(container))

        btn_row.addWidget(approve_btn)
        btn_row.addWidget(reject_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.chat_layout.addWidget(container)
        self._scroll_to_bottom()

    def _on_action_confirmed(self, action_data: dict, container: QFrame) -> None:
        """User clicked Approve on an action step."""
        container.setEnabled(False)
        container.setStyleSheet(container.styleSheet().replace(Colors.WARNING, Colors.SUCCESS))
        self.action_confirmed.emit(action_data)

    def _on_action_rejected(self, container: QFrame) -> None:
        """User clicked Reject on an action step."""
        container.setEnabled(False)
        container.setStyleSheet(container.styleSheet().replace(Colors.WARNING, Colors.DANGER))
        self.add_system_log("Action rejected by user.", color=Colors.DANGER)

    def clear(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._step_widgets = {}

    def _on_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.add_user_message(text)
            self.input_field.clear()
            self.input_submitted.emit(text)

    def _scroll_to_bottom(self):
        # Allow layout to process before scrolling
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
    "pending": Colors.TEXT_SECONDARY,
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
    "highlight_area": "🔍 Highlight",
    "run_command": "⚡ Command",
    "explain": "💡 Explain",
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

        # Step number
        step_label = QLabel(f"{step_num}/{total}")
        step_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.XS}px; font-family: {Fonts.MONO};")
        step_label.setFixedWidth(30)

        # Action type badge
        badge_text = _ACTION_TYPE_LABELS.get(action_type, action_type)
        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            color: {Colors.ACCENT};
            background-color: rgba(186, 158, 255, 0.12);
            border-radius: 4px;
            padding: 2px 6px;
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
        """Update the step's visual status."""
        self._status = status
        icon = _STATUS_ICONS.get(status, "?")
        color = _STATUS_COLORS.get(status, Colors.TEXT_SECONDARY)
        self.status_label.setText(icon)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
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


# Ensure QTimer is available
from PyQt6.QtCore import QTimer


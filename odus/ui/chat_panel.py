"""
Chat Panel — Main interaction panel with message history and action controls.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from odus.ui.theme import (
    Colors, FontSizes, Fonts,
)
from odus.ui.components.chat_bubble import MessageBubble
from odus.ui.components.permission_card import PermissionCard
from odus.ui.components.action_step import ActionStepWidget

logger = logging.getLogger(__name__)

class ChatPanel(QWidget):
    """
    The chat content panel — lives inside OdusMainWindow's content stack.
    """

    action_confirmed = pyqtSignal(dict)
    plan_confirmed = pyqtSignal()

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
        from PyQt6.QtWidgets import QLabel
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

    def add_action_plan(self, summary: str, steps: list[dict], needs_confirmation: bool = False) -> None:
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
        
        if needs_confirmation:
            btn_frame = QFrame()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(0, 8, 0, 8)
            btn_layout.addStretch()
            
            run_btn = QPushButton("▶ Run Implementation Plan")
            run_btn.setFixedWidth(240)
            run_btn.setFixedHeight(36)
            run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            run_btn.setFont(QFont(Fonts.BODY, FontSizes.XS, QFont.Weight.Bold))
            run_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SUCCESS};
                    color: #000000;
                    border: none;
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    background-color: #2dd870;
                }}
                QPushButton:disabled {{
                    background-color: {Colors.BG_SECONDARY};
                    color: {Colors.TEXT_DIM};
                }}
            """)
            
            def on_click():
                btn_frame.setEnabled(False)
                run_btn.setText("✓ Plan Authorized")
                self.plan_confirmed.emit()
                
            run_btn.clicked.connect(on_click)
            btn_layout.addWidget(run_btn)
            self.chat_layout.addWidget(btn_frame)

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

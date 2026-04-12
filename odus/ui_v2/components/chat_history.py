"""
Chat History (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QWidget, QSizePolicy, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from odus.ui_v2.theme import (
    Colors, Spacing, Fonts, FontSizes, Radii
)
from odus.ui_v2.components.chat_bubble import MessageBubbleV2
from odus.ui_v2.components.permission_card import PermissionCardV2
from odus.ui_v2.components.action_step import ActionStepWidgetV2

class ChatHistoryV2(QScrollArea):
    """
    Scrollable chat history with minimal, high-end styling.
    """

    action_confirmed = pyqtSignal(dict)
    plan_confirmed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatHistory")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self._step_widgets = {}
        
        # Scroll area frame
        self.setFrameShape(QFrame.Shape.NoFrame)

        # The content widget
        self.content = QWidget()
        self.content.setObjectName("ChatContent")
        self._layout = QVBoxLayout(self.content)
        self._layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.MD)
        self._layout.setSpacing(Spacing.SM)  # Tighter spacing
        self._layout.addStretch(1) # Start messages from bottom

        self.setWidget(self.content)
        self._apply_style()

    def add_message(self, text: str, is_ai: bool = True):
        """Add a new message bubble to the history."""
        if not text:
            return
        # Insert before the stretch at the bottom
        bubble = MessageBubbleV2(text, is_ai)
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_system_log(self, text: str, color: str = None):
        """Subtle, dimmed log entry that doesn't dominate the chat."""
        if not text:
            return
        log_frame = QFrame()
        log_frame.setObjectName("SystemLog")
        log_layout = QHBoxLayout(log_frame)
        log_layout.setContentsMargins(8, 2, 8, 2)
        log_layout.setSpacing(6)

        # Dim dot indicator
        dot = QLabel("›")
        dot.setFixedWidth(10)
        dot.setStyleSheet(f"color: {color or Colors.TEXT_SECONDARY}; font-size: 10px; opacity: 0.5; background: transparent;")
        log_layout.addWidget(dot)

        log_label = QLabel(text)
        log_label.setWordWrap(True)
        log_label.setStyleSheet(f"""
            color: {color or Colors.TEXT_SECONDARY};
            font-family: '{Fonts.MONO}';
            font-size: {FontSizes.XS - 1}px;
            background: transparent;
            opacity: 0.7;
        """)
        log_layout.addWidget(log_label, stretch=1)

        log_frame.setStyleSheet("background: transparent; border: none;")
        log_frame.setMaximumHeight(24)
        self._layout.insertWidget(self._layout.count() - 1, log_frame)
        self._scroll_to_bottom()

    def add_permission_card(
        self,
        title: str,
        description: str,
        action_data: dict,
        tier: int = 2,
    ) -> PermissionCardV2:
        """Show an inline permission request card."""
        card = PermissionCardV2(title, description, action_data, tier)
        card.allowed.connect(lambda data: self.action_confirmed.emit(data))
        card.denied.connect(lambda: self.add_system_log("Action denied by user.", color=Colors.ERROR))
        self._layout.insertWidget(self._layout.count() - 1, card)
        self._scroll_to_bottom()
        return card

    def add_action_plan(self, summary: str, steps: list[dict], needs_confirmation: bool = False) -> None:
        """Display a multi-step action plan — steps first, summary after."""
        self._step_widgets = {}
        
        plan_container = QWidget()
        plan_layout = QVBoxLayout(plan_container)
        plan_layout.setContentsMargins(0, 0, 0, 0)
        plan_layout.setSpacing(Spacing.SM)
        
        for step in steps:
            step_num = step.get("step", 0)
            total = len(steps)
            action_type = step.get("action_type", "unknown")
            description = step.get("description", "")
            widget = ActionStepWidgetV2(step_num, total, action_type, description)
            self._step_widgets[step_num] = widget
            plan_layout.addWidget(widget)
        
        self._layout.insertWidget(self._layout.count() - 1, plan_container)
        
        if needs_confirmation:
            btn_frame = QFrame()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(0, 8, 0, 8)
            btn_layout.setSpacing(Spacing.SM)
            
            run_btn = QPushButton("Execute Implementation Plan")
            run_btn.setFixedHeight(36)
            run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            run_btn.setFont(QFont(Fonts.HEADLINE, FontSizes.XS, QFont.Weight.Bold))
            run_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: {Colors.BG_BASE};
                    border: none;
                    border-radius: {Radii.MD}px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_CONTAINER};
                }}
                QPushButton:disabled {{
                    background-color: {Colors.BG_LEVEL_1};
                    color: {Colors.TEXT_SECONDARY};
                }}
            """)
            
            def on_click():
                btn_frame.setEnabled(False)
                run_btn.setText("Plan Authorized")
                self.plan_confirmed.emit()
                
            run_btn.clicked.connect(on_click)
            btn_layout.addWidget(run_btn)
            self._layout.insertWidget(self._layout.count() - 1, btn_frame)

        self._scroll_to_bottom()

    def update_action_step(self, step_num: int, status: str) -> None:
        widget = self._step_widgets.get(step_num)
        if widget:
            widget.set_status(status)
            self._scroll_to_bottom()

    def clear(self):
        """Clear the history."""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._step_widgets = {}

    def _scroll_to_bottom(self):
        """Smoothly scroll to the bottom of history."""
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        ))

    def _apply_style(self):
        self.setStyleSheet(f"""
            QScrollArea#ChatHistory {{
                background-color: transparent;
                border: none;
            }}
            QWidget#ChatContent {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_GHOST};
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
                border: none;
            }}
        """)

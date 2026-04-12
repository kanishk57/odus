"""
Message Bubble (v2) — Polished chat cards.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from odus.ui_v2.theme import (
    Colors, FontSizes, Radii, Spacing, Fonts
)


class MessageBubbleV2(QFrame):
    """
    Polished message bubble with visual distinction between AI and user.
    AI: tinted card with left accent bar.
    User: right-aligned rounded bubble.
    """

    def __init__(self, text: str, is_ai: bool = True):
        super().__init__()
        self.setObjectName("MsgBubble")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        self._layout.setSpacing(0)

        if is_ai:
            self._build_ai_bubble(text)
        else:
            self._build_user_bubble(text)

        self._animate_entrance()

    def _build_ai_bubble(self, text: str):
        """AI message: accent-bar card with tinted background."""
        card = QFrame()
        card.setObjectName("AiCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Left accent bar
        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet(f"""
            background-color: {Colors.PRIMARY};
            border-top-left-radius: 2px;
            border-bottom-left-radius: 2px;
        """)
        card_layout.addWidget(accent)

        # Message text
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setFont(QFont(Fonts.BODY, FontSizes.MD))
        label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            padding: 12px 16px;
            background: transparent;
            line-height: 1.6;
        """)
        card_layout.addWidget(label, stretch=1)

        card.setStyleSheet(f"""
            QFrame#AiCard {{
                background-color: {Colors.BG_LEVEL_1};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

        self._layout.addWidget(card)
        self.setStyleSheet("background-color: transparent; border: none;")

    def _build_user_bubble(self, text: str):
        """User message: right-aligned rounded bubble."""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setFont(QFont(Fonts.BODY, FontSizes.MD))
        label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            background: transparent;
            line-height: 1.6;
        """)

        bubble = QFrame()
        bubble.setObjectName("UserBubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 10, 16, 10)
        bubble_layout.addWidget(label)

        bubble.setStyleSheet(f"""
            QFrame#UserBubble {{
                background-color: {Colors.BG_LEVEL_2};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER_GHOST};
            }}
        """)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(bubble, stretch=4)
        self._layout.addLayout(row)
        self.setStyleSheet("background-color: transparent; border: none;")

    def _animate_entrance(self):
        """Fade-in entrance."""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self.anim = QPropertyAnimation(effect, b"opacity", self)
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

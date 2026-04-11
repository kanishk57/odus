"""
Message Bubble — Stylized containers for AI and User messages.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from odus.ui.theme import (
    Colors, FontSizes, Radii, Animations,
)

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

"""
Message Bubble (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from odus.ui_v2.theme import (
    Colors, FontSizes, Radii, Spacing, Fonts
)

class MessageBubbleV2(QFrame):
    """A technical, minimal message bubble for the sidebar."""

    def __init__(self, text: str, is_ai: bool = True):
        super().__init__()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        self._layout.setSpacing(Spacing.XS)

        # Container for the bubble to handle max-width simulation
        self.container = QFrame()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Max width simulation: we don't strictly have max-width in Qt layouts easily
        # but we can use stretch in the parent layout.
        
        if is_ai:
            # Assistant Bubble: Transparent background, left-aligned
            self.label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.BODY}';
                font-size: {FontSizes.MD}px;
                line-height: 1.5;
                background-color: transparent;
            """)
            self._layout.addWidget(self.label)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.setStyleSheet("background-color: transparent; border: none;")
        else:
            # User Bubble: Nesting Level 2 background, right-aligned
            self.label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.BODY}';
                font-size: {FontSizes.MD}px;
                line-height: 1.5;
                background-color: transparent;
            """)
            
            self.bubble_frame = QFrame()
            self.bubble_frame.setObjectName("UserBubbleFrame")
            bubble_layout = QVBoxLayout(self.bubble_frame)
            bubble_layout.setContentsMargins(12, 8, 12, 8)
            bubble_layout.addWidget(self.label)
            
            self.bubble_frame.setStyleSheet(f"""
                QFrame#UserBubbleFrame {{
                    background-color: {Colors.BG_LEVEL_2};
                    border-radius: {Radii.MD}px;
                    border: 1px solid {Colors.BORDER_GHOST};
                }}
            """)
            
            # Use a horizontal layout to push the bubble to the right
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(self.bubble_frame, stretch=4) # Simulate ~80% max width
            self._layout.addLayout(row)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Entrance animation
        self._animate_entrance()

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

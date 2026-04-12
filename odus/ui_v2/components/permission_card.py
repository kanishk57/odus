"""
Permission Card (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from odus.ui_v2.theme import (
    Colors, FontSizes, Fonts, Radii, Spacing
)

class PermissionCardV2(QFrame):
    """
    Inline permission request card for the sidebar.
    """

    allowed = pyqtSignal(dict)
    denied = pyqtSignal()

    def __init__(self, title: str, description: str, action_data: dict, tier: int = 2, parent=None):
        super().__init__(parent)
        self.setObjectName("PermissionCard")
        self._action_data = action_data
        self._tier = tier

        tier_color = {1: Colors.SUCCESS, 2: Colors.WARNING, 3: Colors.ERROR}.get(tier, Colors.WARNING)
        tier_label = {1: "SAFE", 2: "CAUTION", 3: "DANGER"}.get(tier, "CAUTION")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Header row: tier badge + title
        header = QHBoxLayout()
        header.setSpacing(Spacing.SM)

        badge = QLabel(tier_label)
        badge.setFont(QFont(Fonts.HEADLINE, FontSizes.XS, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            color: {tier_color};
            background-color: transparent;
            border: 1px solid {tier_color};
            border-radius: {Radii.SM}px;
            padding: 2px 8px;
            letter-spacing: 1px;
        """)
        header.addWidget(badge)

        title_label = QLabel(title)
        title_label.setFont(QFont(Fonts.HEADLINE, FontSizes.SM, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        title_label.setWordWrap(True)
        header.addWidget(title_label, stretch=1)
        layout.addLayout(header)

        # Description
        desc = QLabel(description)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-family: '{Fonts.BODY}'; font-size: {FontSizes.SM}px; line-height: 1.4;")
        layout.addWidget(desc)

        # Command preview (if present)
        command = action_data.get("command", "") or action_data.get("text", "")
        if command:
            cmd_frame = QFrame()
            cmd_frame.setObjectName("CmdPreview")
            cmd_frame.setStyleSheet(f"""
                QFrame#CmdPreview {{
                    background-color: {Colors.BG_LOWEST};
                    border-radius: {Radii.SM}px;
                    border: 1px solid {Colors.BORDER_GHOST};
                    padding: 8px;
                }}
            """)
            cmd_layout = QVBoxLayout(cmd_frame)
            cmd_layout.setContentsMargins(8, 8, 8, 8)
            cmd_label = QLabel(f"$ {command}")
            cmd_label.setFont(QFont(Fonts.MONO, FontSizes.XS))
            cmd_label.setStyleSheet(f"color: {Colors.PRIMARY};")
            cmd_label.setWordWrap(True)
            cmd_layout.addWidget(cmd_label)
            layout.addWidget(cmd_frame)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(Spacing.SM)

        deny_btn = QPushButton("Deny")
        deny_btn.setFixedHeight(32)
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.setFont(QFont(Fonts.HEADLINE, FontSizes.XS, QFont.Weight.Bold))
        deny_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER_GHOST};
                border-radius: {Radii.SM}px;
            }}
            QPushButton:hover {{
                color: {Colors.ERROR};
                border-color: {Colors.ERROR};
            }}
        """)

        allow_btn = QPushButton("Authorize")
        allow_btn.setFixedHeight(32)
        allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        allow_btn.setFont(QFont(Fonts.HEADLINE, FontSizes.XS, QFont.Weight.Bold))
        allow_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: {Colors.BG_BASE};
                border: none;
                border-radius: {Radii.SM}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_CONTAINER};
            }}
        """)

        deny_btn.clicked.connect(self._on_deny)
        allow_btn.clicked.connect(self._on_allow)

        btn_row.addWidget(deny_btn, stretch=1)
        btn_row.addWidget(allow_btn, stretch=1)
        layout.addLayout(btn_row)

        # Card styling
        self.setStyleSheet(f"""
            QFrame#PermissionCard {{
                background-color: {Colors.BG_LEVEL_1};
                border-radius: {Radii.MD}px;
                border: 1px solid {Colors.BORDER_GHOST};
            }}
        """)

        # Entrance animation
        self._animate_entrance()

    def _on_allow(self):
        self.setEnabled(False)
        self.allowed.emit(self._action_data)

    def _on_deny(self):
        self.setEnabled(False)
        self.denied.emit()

    def _animate_entrance(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self.anim = QPropertyAnimation(effect, b"opacity", self)
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

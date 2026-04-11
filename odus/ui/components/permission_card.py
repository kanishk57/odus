"""
Permission Card — Inline authorization requests.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from odus.ui.theme import (
    Colors, FontSizes, Fonts, Radii, Animations,
)

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
        title_label.setWordWrap(True)
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

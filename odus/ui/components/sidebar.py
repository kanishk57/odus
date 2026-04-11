"""
Mascot Sidebar — Avatar, status badges, and quick actions.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QPushButton, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from odus.ui.theme import (
    Colors, Fonts, FontSizes, Gradients, Layout, Radii,
)
from odus.ui.mascot import MascotWidget

class MascotSidebar(QFrame):
    """
    Left sidebar with mascot, status badges, and quick-action buttons.
    """

    capture_requested = pyqtSignal()
    browse_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MascotSidebar")
        self.setFixedWidth(Layout.SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # ── Mascot ──
        self.mascot = MascotWidget()
        layout.addWidget(self.mascot, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── Status label ──
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont(Fonts.BODY, FontSizes.XS))
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 4px;")
        layout.addWidget(self.status_label)

        # ── Divider ──
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {Colors.BORDER_SUBTLE}; margin: 4px 20px;")
        layout.addWidget(div)

        # ── Quick actions ──
        self.capture_btn = self._make_action_btn("📸", "Capture Screen")
        self.capture_btn.clicked.connect(self.capture_requested.emit)
        layout.addWidget(self.capture_btn)

        self.browse_btn = self._make_action_btn("📂", "Browse Files")
        self.browse_btn.clicked.connect(self.browse_requested.emit)
        layout.addWidget(self.browse_btn)

        layout.addStretch()

        # ── Safety tier indicator at bottom ──
        self.tier_badge = QLabel("● SAFE")
        self.tier_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tier_badge.setFont(QFont(Fonts.MONO, FontSizes.XS, QFont.Weight.Bold))
        self.tier_badge.setStyleSheet(f"""
            color: {Colors.SUCCESS};
            background-color: {Colors.SUCCESS_GLOW};
            border-radius: 10px;
            padding: 4px 12px;
            margin: 0 20px;
        """)
        layout.addWidget(self.tier_badge)

        self._apply_style()

    def set_status(self, text: str, color: str = Colors.TEXT_SECONDARY) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; padding: 4px;")

    def set_tier(self, tier: int) -> None:
        colors = {1: Colors.SUCCESS, 2: Colors.WARNING, 3: Colors.DANGER}
        glows = {1: Colors.SUCCESS_GLOW, 2: Colors.WARNING_GLOW, 3: Colors.DANGER_GLOW}
        labels = {1: "● SAFE", 2: "● CAUTION", 3: "● DANGER"}
        c = colors.get(tier, Colors.TEXT_SECONDARY)
        g = glows.get(tier, "transparent")
        l = labels.get(tier, "● UNKNOWN")
        self.tier_badge.setText(l)
        self.tier_badge.setStyleSheet(f"""
            color: {c};
            background-color: {g};
            border-radius: 10px;
            padding: 4px 12px;
            margin: 0 20px;
        """)

    def _make_action_btn(self, icon: str, tooltip: str) -> QPushButton:
        btn = QPushButton(f"  {icon}  {tooltip}")
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont(Fonts.BODY, FontSizes.XS))
        btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: {Radii.SM}px;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)
        return btn

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#MascotSidebar {{
                background: {Gradients.SIDEBAR};
                border-right: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

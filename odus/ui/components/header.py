"""
Header Bar — Top navigation and branding.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt

from odus.ui.theme import (
    Colors, Fonts, FontSizes, Gradients, Layout,
)

class HeaderBar(QFrame):
    """
    Top header bar with logo and tabs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(Layout.HEADER_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # Sidebar toggle button
        self.toggle_sidebar_btn = QPushButton("☰")
        self.toggle_sidebar_btn.setFixedSize(28, 28)
        self.toggle_sidebar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_sidebar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                font-size: 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY};
                background-color: {Colors.BG_ELEVATED};
            }}
        """)
        layout.addWidget(self.toggle_sidebar_btn)
        layout.addSpacing(8)

        # Logo
        logo = QLabel("ODUS")
        logo.setFont(QFont(Fonts.HEADING, FontSizes.MD, QFont.Weight.Bold))
        logo.setStyleSheet(f"""
            color: {Colors.ACCENT};
            letter-spacing: 3px;
            padding-left: 4px;
        """)
        layout.addWidget(logo)

        # Status dot (will be updated by app)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 8px; padding-left: 8px;")
        layout.addWidget(self.status_dot)

        # Spacer label
        spacer = QLabel("")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(spacer)

        # Tab switcher buttons
        self.tab_chat_btn = QPushButton("💬 Chat")
        self.tab_term_btn = QPushButton("⚡ Terminal")
        for btn in (self.tab_chat_btn, self.tab_term_btn):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(Fonts.BODY, FontSizes.XS))
        self._style_tab_btn(self.tab_chat_btn, active=True)
        self._style_tab_btn(self.tab_term_btn, active=False)
        layout.addWidget(self.tab_chat_btn)
        layout.addWidget(self.tab_term_btn)

        self._apply_style()

    def set_active_tab(self, tab: str) -> None:
        self._style_tab_btn(self.tab_chat_btn, active=(tab == "chat"))
        self._style_tab_btn(self.tab_term_btn, active=(tab == "terminal"))

    def _style_tab_btn(self, btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.ACCENT_GLOW};
                    color: {Colors.ACCENT};
                    border: 1px solid {Colors.BORDER_ACTIVE};
                    border-radius: 14px;
                    padding: 4px 14px;
                    font-weight: bold;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_SECONDARY};
                    border: 1px solid transparent;
                    border-radius: 14px;
                    padding: 4px 14px;
                }}
                QPushButton:hover {{
                    color: {Colors.TEXT_PRIMARY};
                    background-color: {Colors.BG_ELEVATED};
                }}
            """)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#HeaderBar {{
                background: {Gradients.HEADER};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

# Fix missing import in extracted code
from PyQt6.QtGui import QFont

"""
Sidebar Header (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

from odus.ui_v2.theme import (
    Colors, FontSizes, Radii, Spacing, Fonts
)

class SidebarHeaderV2(QFrame):
    """
    Top section of the sidebar with mascot and title.
    """

    close_clicked = pyqtSignal()
    quit_requested = pyqtSignal()
    mascot_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarHeader")
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(Spacing.LG, Spacing.XL, Spacing.LG, Spacing.MD)
        self._layout.setSpacing(Spacing.SM)

        # Mascot + Actions Row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        
        self.mascot_btn = QPushButton()
        self.mascot_btn.setFixedSize(48, 48)
        self.mascot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mascot_btn.setObjectName("MascotBtn")
        self.mascot_btn.clicked.connect(self.mascot_clicked)
        
        # Internal label for image
        self.mascot_icon = QLabel("🦉")
        self.mascot_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        btn_layout = QVBoxLayout(self.mascot_btn)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(self.mascot_icon)
        
        # Try to load actual mascot image if it exists
        pixmap = QPixmap("assets/mascot_idle.png")
        if not pixmap.isNull():
            self.mascot_icon.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.mascot_icon.setText("")

        top_row.addWidget(self.mascot_btn)
        top_row.addStretch()

        # Action Buttons (Quit then Collapse)
        self.quit_btn = QPushButton("⏻") # Power icon
        self.quit_btn.setFixedSize(32, 32)
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.setObjectName("QuitBtn")
        self.quit_btn.setToolTip("Quit Odus")
        self.quit_btn.clicked.connect(self.quit_requested)
        top_row.addWidget(self.quit_btn)
        
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setToolTip("Collapse")
        self.close_btn.clicked.connect(self.close_clicked)
        top_row.addWidget(self.close_btn)
        
        self._layout.addLayout(top_row)

        # Title
        self.title = QLabel("ODUS")
        self.title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Fonts.HEADLINE}';
            font-size: {FontSizes.XL}px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        self._layout.addWidget(self.title)

        # Subtitle / Status
        self.subtitle = QLabel("THE SHADOW CONSOLE")
        self.subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-family: '{Fonts.HEADLINE}';
            font-size: {FontSizes.XS}px;
            letter-spacing: 1px;
        """)
        self._layout.addWidget(self.subtitle)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#SidebarHeader {{
                background-color: transparent;
            }}
            QPushButton#MascotBtn {{
                background-color: {Colors.BG_LEVEL_1};
                border-radius: {Radii.MD}px;
                border: 1px solid {Colors.BORDER_GHOST};
            }}
            QPushButton#MascotBtn:hover {{
                background-color: {Colors.BG_LEVEL_2};
                border-color: {Colors.PRIMARY};
            }}
            QPushButton#CloseBtn {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-size: 24px;
                border: none;
            }}
            QPushButton#CloseBtn:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton#QuitBtn {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                font-size: 18px;
                border: none;
            }}
            QPushButton#QuitBtn:hover {{
                color: {Colors.ERROR};
            }}
        """)

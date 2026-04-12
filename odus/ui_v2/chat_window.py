"""
Standard 16:9 Chat Window (v2) — Editorial Obsidian Style.
Fallback for users who prefer a traditional window over the sidebar.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QWidget, QMainWindow, QApplication, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

from odus.ui_v2.theme import (
    Colors, Layout, Spacing, Radii, Fonts
)
from odus.ui_v2.components.header import SidebarHeaderV2
from odus.ui_v2.components.chat_history import ChatHistoryV2
from odus.ui_v2.components.input_bar import InputBarV2
from odus.ui_v2.components.ghost_terminal import GhostTerminalV2

class ChatWindowV2(QMainWindow):
    """
    Standard window fallback.
    Features 16:9 aspect ratio, minimize, maximize, and fullscreen.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Odus")
        self.setMinimumSize(640, 360)
        self.resize(Layout.WINDOW_INITIAL_WIDTH, Layout.WINDOW_INITIAL_HEIGHT)

        # Style for main window
        self.setStyleSheet(f"background-color: {Colors.BG_BASE};")

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Components (Reused from Sidebar)
        self.header = SidebarHeaderV2()
        # In a standard window, 'close' should maybe just minimize or hide?
        # But for consistency we'll keep the signals.
        
        # Override header styling for a full window
        self.header.setStyleSheet(f"background-color: {Colors.BG_LEVEL_1}; border-bottom: 1px solid {Colors.BORDER_GHOST};")

        # Content Area (Horizontal for a wide window)
        self.content_frame = QFrame()
        self.content_layout = QHBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        self.content_layout.setSpacing(Spacing.MD)

        self.chat_history = ChatHistoryV2()
        self.terminal = GhostTerminalV2()
        
        self.content_layout.addWidget(self.chat_history, stretch=2)
        self.content_layout.addWidget(self.terminal, stretch=1)

        self.input_bar = InputBarV2()

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_frame, stretch=1)
        self.main_layout.addWidget(self.input_bar)

    def set_mascot_state(self, state: str):
        """Update mascot icon in the header."""
        icon_map = {
            "idle": "assets/mascot_idle.png",
            "thinking": "assets/mascot_thinking.png",
            "success": "assets/mascot_success.png",
            "error": "assets/mascot_error.png",
            "warning": "assets/mascot_warning.png",
        }
        path = icon_map.get(state, icon_map["idle"])
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return

        self.header.mascot_icon.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.header.mascot_icon.setText("")

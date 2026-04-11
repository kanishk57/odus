"""
Chat Interface — Modern Obsidian/Glass chat UI for Odus.
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextEdit, QLineEdit, QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from odus.ui.theme import Colors, FontSizes, Fonts, Radii

logger = logging.getLogger(__name__)


class MessageBubble(QFrame):
    """A stylized message bubble with Glassmorphism support."""
    
    def __init__(self, text: str, is_ai: bool = True):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Styles
        if is_ai:
            self.setObjectName("AiBubble")
            bg = Colors.BG_GLASS
            color = Colors.TEXT_PRIMARY
            self.label.setStyleSheet(f"color: {color}; line-height: 1.6;")
        else:
            self.setObjectName("UserBubble")
            bg = "transparent"
            color = Colors.ACCENT
            self.label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.setStyleSheet(f"""
            QFrame#AiBubble {{
                background-color: {bg};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER};
            }}
            QFrame#UserBubble {{
                background-color: {bg};
            }}
        """)
        
        self.layout.addWidget(self.label)


class ChatInterface(QWidget):
    """
    The new primary interaction window for Odus.
    Combines AI chat bubbles with a command input pill.
    """
    
    input_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatInterface")
        self.setMinimumSize(400, 600)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # 1. Header
        header = QHBoxLayout()
        title = QLabel("ODUS")
        title.setStyleSheet(f"color: {Colors.ACCENT}; font-weight: bold; letter-spacing: 2px;")
        title.setFont(QFont(Fonts.HEADING, FontSizes.MD))
        header.addWidget(title)
        header.addStretch()
        self.layout.addLayout(header)

        # 2. Chat Area (Scrollable)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(20)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll.setWidget(self.chat_container)
        self.layout.addWidget(self.scroll)

        # 3. Input Pill
        self.input_container = QFrame()
        self.input_container.setObjectName("InputContainer")
        self.input_container.setFixedHeight(50)
        
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(15, 0, 10, 0)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Odus something...")
        self.input_field.setFrame(False)
        self.input_field.setObjectName("CommandInput")
        self.input_field.returnPressed.connect(self._on_submit)
        
        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.clicked.connect(self._on_submit)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        self.layout.addWidget(self.input_container)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QWidget#ChatInterface {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: {Radii.LG}px;
                border: 1px solid {Colors.BORDER};
            }}
            QFrame#InputContainer {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 25px;
                border: 1px solid {Colors.BORDER};
            }}
            QLineEdit#CommandInput {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.MD}px;
            }}
            QPushButton#SendBtn {{
                background-color: {Colors.ACCENT};
                color: #000000;
                border-radius: 15px;
                font-weight: bold;
            }}
            QPushButton#SendBtn:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER};
                border-radius: 2px;
            }}
        """)

    def add_ai_message(self, text: str):
        bubble = MessageBubble(text, is_ai=True)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_user_message(self, text: str):
        bubble = MessageBubble(text, is_ai=False)
        self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_system_log(self, text: str, color: str = None):
        """Minimalist log entry for terminal outputs."""
        log_label = QLabel(f"› {text}")
        log_label.setStyleSheet(f"color: {color or Colors.TEXT_SECONDARY}; font-family: {Fonts.MONO}; font-size: {FontSizes.XS}px;")
        log_label.setWordWrap(True)
        self.chat_layout.addWidget(log_label)
        self._scroll_to_bottom()

    def clear(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.add_user_message(text)
            self.input_field.clear()
            self.input_submitted.emit(text)

    def _scroll_to_bottom(self):
        # Allow layout to process before scrolling
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

# Ensure QTimer is available
from PyQt6.QtCore import QTimer

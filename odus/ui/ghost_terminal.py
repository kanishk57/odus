"""
Ghost Terminal — scrollable terminal output visualizer in PyQt6.
"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon

from odus.ui.theme import Colors, FontSizes, Fonts, Radii

logger = logging.getLogger(__name__)


class GhostTerminal(QWidget):
    """
    Terminal-like output display for the Odus UI in PyQt6.
    Uses QTextEdit with HTML appending for colors.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GhostTerminal")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Header
        self.header = QWidget()
        self.header.setObjectName("TerminalHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        title = QLabel("Ghost Terminal")
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: bold;")
        title.setFont(QFont(Fonts.MONO, FontSizes.SM))
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("ClearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)

        # Output Area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("TerminalOutput")
        font = QFont(Fonts.MONO, FontSizes.SM)
        self.output.setFont(font)
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        self.layout.addWidget(self.header)
        self.layout.addWidget(self.output)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QWidget#GhostTerminal {{
                background-color: rgba(15, 17, 23, 0.85);
                border-radius: {Radii.LG}px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QWidget#TerminalHeader {{
                background-color: rgba(255, 255, 255, 0.03);
                border-top-left-radius: {Radii.LG}px;
                border-top-right-radius: {Radii.LG}px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QPushButton#ClearBtn {{
                color: {Colors.TEXT_SECONDARY};
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: {Radii.SM}px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton#ClearBtn:hover {{
                background: rgba(255, 255, 255, 0.1);
                color: {Colors.TEXT_PRIMARY};
            }}
            QTextEdit#TerminalOutput {{
                background-color: transparent;
                color: {Colors.TERMINAL_TEXT};
                border: none;
                padding: 15px;
            }}
        """)

    # ── Public API ──────────────────────────────────────────────────────

    def add_info(self, text: str) -> None:
        self._add_entry(text, Colors.TERMINAL_TEXT, "›")

    def add_success(self, text: str) -> None:
        self._add_entry(text, Colors.TERMINAL_GREEN, "✓")

    def add_error(self, text: str) -> None:
        self._add_entry(text, Colors.TERMINAL_RED, "✗")

    def add_warning(self, text: str) -> None:
        self._add_entry(text, Colors.TERMINAL_YELLOW, "⚠")

    def add_command(self, command: str) -> None:
        self._add_entry(
            f"$ {command}",
            Colors.TERMINAL_BLUE,
            "▶",
            bold=True,
        )

    def add_output(self, text: str) -> None:
        for line in text.strip().split("\n"):
            self._add_entry(line, Colors.TEXT_SECONDARY, "&nbsp;&nbsp;")

    def add_divider(self) -> None:
        self.output.append(f"<hr style='border: 1px solid {Colors.BORDER}; margin: 5px 0;'>")

    def clear(self) -> None:
        self.output.clear()

    # ── Private ─────────────────────────────────────────────────────────

    def _add_entry(
        self,
        text: str,
        color: str,
        prefix: str = "›",
        bold: bool = False,
    ) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        weight = "bold" if bold else "normal"
        
        # Escape HTML chars in text
        escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        html = f"""
        <div style='margin-bottom: 4px; white-space: pre-wrap;'>
            <span style='color: rgba(255,255,255,0.4); font-size: 11px;'>{timestamp}</span>
            <span style='color: {color}; margin-left: 8px;'>{prefix}</span>
            <span style='color: {color}; font-weight: {weight}; margin-left: 8px;'>{escaped_text}</span>
        </div>
        """
        self.output.append(html)
        
        # Scroll to bottom
        scrollbar = self.output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

"""
Ghost Terminal (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from odus.ui_v2.theme import Colors, FontSizes, Fonts, Radii, Spacing

# ── ANSI Color Map ─────────────────────────────────────────────────────

_ANSI_COLORS = {
    "31": Colors.ERROR,
    "32": Colors.SUCCESS,
    "33": Colors.WARNING,
    "34": Colors.PRIMARY,
    "35": "#c084fc", # Magenta
    "36": "#22d3ee", # Cyan
    "37": Colors.TEXT_PRIMARY,
    "90": Colors.TEXT_SECONDARY,
    "91": Colors.ERROR,
    "92": Colors.SUCCESS,
    "93": Colors.WARNING,
    "94": Colors.PRIMARY,
}

_ANSI_PATTERN = re.compile(r'\033\[([0-9;]*)m')

def _ansi_to_html(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    result = []
    last_end = 0
    open_spans = 0
    for match in _ANSI_PATTERN.finditer(text):
        result.append(text[last_end:match.start()])
        codes = match.group(1).split(";")
        for code in codes:
            code = code.strip()
            if code == "0" or code == "":
                for _ in range(open_spans):
                    result.append("</span>")
                open_spans = 0
            elif code == "1":
                result.append("<span style='font-weight: bold;'>")
                open_spans += 1
            elif code in _ANSI_COLORS:
                color = _ANSI_COLORS[code]
                result.append(f"<span style='color: {color};'>")
                open_spans += 1
        last_end = match.end()
    result.append(text[last_end:])
    for _ in range(open_spans):
        result.append("</span>")
    return "".join(result)

class GhostTerminalV2(QWidget):
    """Terminal-like output display for the sidebar."""

    MAX_LINES = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GhostTerminal")
        self._line_count = 0
        self._html_buffer = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_buffer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # CWD Bar
        self.cwd_bar = QFrame()
        cwd_layout = QHBoxLayout(self.cwd_bar)
        cwd_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cwd_label = QLabel("~")
        self.cwd_label.setFont(QFont(Fonts.MONO, FontSizes.XS))
        self.cwd_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.cwd_label.setWordWrap(True)
        cwd_layout.addWidget(self.cwd_label, stretch=1)

        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: {Colors.TEXT_SECONDARY};
                background: transparent;
                border: 1px solid {Colors.BORDER_GHOST};
                border-radius: {Radii.SM}px;
                padding: 2px 8px;
                font-family: '{Fonts.HEADLINE}';
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
        """)
        cwd_layout.addWidget(self.clear_btn)
        layout.addWidget(self.cwd_bar)

        # Output Area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont(Fonts.MONO, FontSizes.SM))
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_LOWEST};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_GHOST};
                border-radius: {Radii.MD}px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_GHOST};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.output)

    def set_cwd(self, path: str) -> None:
        import os
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        self.cwd_label.setText(path)

    def _flush_buffer(self) -> None:
        if not self._html_buffer:
            return
        combined_html = "<br>".join(self._html_buffer)
        self.output.append(combined_html)
        self._html_buffer.clear()
        self._scroll_to_bottom()

    def add_stream_line(self, text: str) -> None:
        html_line = _ansi_to_html(text.rstrip("\n\r"))
        self._html_buffer.append(f"<span style='white-space: pre-wrap; font-family: {Fonts.MONO};'>{html_line}</span>")
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def add_success(self, text: str) -> None:
        self._add_entry(text, Colors.SUCCESS, "✓")

    def add_error(self, text: str) -> None:
        self._add_entry(text, Colors.ERROR, "✗")

    def add_command(self, command: str) -> None:
        self._add_entry(f"$ {command}", Colors.PRIMARY, "▶", bold=True)

    def add_output(self, text: str) -> None:
        for line in text.strip().split("\n"):
            html = _ansi_to_html(line)
            self.output.append(f"<span style='color: {Colors.TEXT_SECONDARY}; font-family: {Fonts.MONO};'>  {html}</span>")
        self._scroll_to_bottom()

    def clear(self) -> None:
        self.output.clear()
        self._line_count = 0

    def _add_entry(self, text: str, color: str, prefix: str = "›", bold: bool = False) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        weight = "bold" if bold else "normal"
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = (
            f"<div style='margin-bottom: 2px; white-space: pre-wrap;'>"
            f"<span style='color: {Colors.TEXT_SECONDARY}; font-size: 10px; opacity: 0.5;'>{timestamp}</span>"
            f"<span style='color: {color}; margin-left: 6px;'>{prefix}</span>"
            f"<span style='color: {color}; font-weight: {weight}; margin-left: 6px;'>{escaped}</span>"
            f"</div>"
        )
        self.output.append(html)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(30, lambda: self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        ))

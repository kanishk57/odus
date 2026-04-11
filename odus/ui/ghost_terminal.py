"""
Ghost Terminal — real-time streaming terminal output with ANSI color support.

Lives inside OdusMainWindow's content stack as the "terminal" tab.
Streams command output line-by-line from the PTY session.
"""

import logging
import re
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from odus.ui.theme import Colors, FontSizes, Fonts, Radii

logger = logging.getLogger(__name__)

# ── ANSI Color Map ─────────────────────────────────────────────────────

_ANSI_COLORS = {
    "30": Colors.TEXT_DIM,         # Black (use dim instead of invisible)
    "31": Colors.TERMINAL_RED,     # Red
    "32": Colors.TERMINAL_GREEN,   # Green
    "33": Colors.TERMINAL_YELLOW,  # Yellow
    "34": Colors.TERMINAL_BLUE,    # Blue
    "35": Colors.TERMINAL_MAGENTA, # Magenta
    "36": Colors.TERMINAL_CYAN,    # Cyan
    "37": Colors.TERMINAL_WHITE,   # White
    "90": Colors.TEXT_DIM,         # Bright Black (gray)
    "91": Colors.DANGER,           # Bright Red
    "92": Colors.SUCCESS,          # Bright Green
    "93": Colors.WARNING,          # Bright Yellow
    "94": Colors.ACCENT,           # Bright Blue
    "95": Colors.TERMINAL_MAGENTA, # Bright Magenta
    "96": Colors.TERMINAL_CYAN,    # Bright Cyan
    "97": Colors.TEXT_PRIMARY,     # Bright White
}

_ANSI_PATTERN = re.compile(r'\033\[([0-9;]*)m')


def _ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML spans."""
    # Escape HTML first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    result = []
    last_end = 0
    open_spans = 0

    for match in _ANSI_PATTERN.finditer(text):
        # Add text before this escape code
        result.append(text[last_end:match.start()])

        codes = match.group(1).split(";")
        for code in codes:
            code = code.strip()
            if code == "0" or code == "":
                # Reset
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

    # Close any unclosed spans
    for _ in range(open_spans):
        result.append("</span>")

    return "".join(result)


# ── Ghost Terminal Widget ──────────────────────────────────────────────

class GhostTerminal(QWidget):
    """
    Terminal-like output display with real-time streaming and ANSI colors.

    Lives inside the unified window's content stack as the "terminal" tab.
    """

    MAX_LINES = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GhostTerminal")
        self.setProperty("tab_name", "terminal")
        self._line_count = 0
        
        self._html_buffer = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)  # Flush every 50ms
        self._flush_timer.timeout.connect(self._flush_buffer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── CWD Indicator ──
        self.cwd_bar = QFrame()
        self.cwd_bar.setObjectName("CwdBar")
        self.cwd_bar.setFixedHeight(32)
        cwd_layout = QHBoxLayout(self.cwd_bar)
        cwd_layout.setContentsMargins(16, 0, 16, 0)

        cwd_icon = QLabel("📂")
        cwd_icon.setStyleSheet("font-size: 12px;")
        cwd_layout.addWidget(cwd_icon)

        self.cwd_label = QLabel("~")
        self.cwd_label.setFont(QFont(Fonts.MONO, FontSizes.XS))
        self.cwd_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self.cwd_label.setWordWrap(True)
        cwd_layout.addWidget(self.cwd_label, stretch=1)

        cwd_layout.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("ClearBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear)
        cwd_layout.addWidget(self.clear_btn)

        layout.addWidget(self.cwd_bar)

        # ── Output Area ──
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("TerminalOutput")
        self.output.setFont(QFont(Fonts.MONO, FontSizes.SM))
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.output)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QWidget#GhostTerminal {{
                background-color: {Colors.TERMINAL_BG};
            }}
            QFrame#CwdBar {{
                background-color: rgba(255, 255, 255, 0.03);
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
            QPushButton#ClearBtn {{
                color: {Colors.TEXT_DIM};
                background: transparent;
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.SM}px;
                padding: 2px 10px;
                font-size: {FontSizes.XS}px;
                font-family: {Fonts.MONO};
            }}
            QPushButton#ClearBtn:hover {{
                background: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT_SECONDARY};
            }}
            QTextEdit#TerminalOutput {{
                background-color: transparent;
                color: {Colors.TERMINAL_TEXT};
                border: none;
                padding: 12px 16px;
                selection-background-color: rgba(186, 158, 255, 0.3);
            }}
            QScrollBar:vertical {{
                border: none; background: transparent; width: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER}; border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    # ── Public API ─────────────────────────────────────────────────────

    def set_cwd(self, path: str) -> None:
        """Update the working directory indicator."""
        # Shorten home directory
        import os
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        self.cwd_label.setText(path)

    def _flush_buffer(self) -> None:
        """Flush accumulated HTML lines to the UI."""
        if not self._html_buffer:
            return
            
        combined_html = "<br>".join(self._html_buffer)
        self.output.append(combined_html)
        self._html_buffer.clear()
        self._enforce_scrollback()
        self._scroll_to_bottom()

    def add_stream_line(self, text: str) -> None:
        """
        Append a single line of streaming output.
        Supports ANSI escape codes. Buffers internally to prevent UI freezing.
        """
        html_line = _ansi_to_html(text.rstrip("\n\r"))
        self._html_buffer.append(f"<span style='white-space: pre-wrap; font-family: {Fonts.MONO};'>{html_line}</span>")
        
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def add_success(self, text: str) -> None:
        self._add_entry(text, Colors.TERMINAL_GREEN, "✓")

    def add_error(self, text: str) -> None:
        self._add_entry(text, Colors.TERMINAL_RED, "✗")

    def add_command(self, command: str) -> None:
        self._add_entry(f"$ {command}", Colors.TERMINAL_BLUE, "▶", bold=True)

    def add_output(self, text: str) -> None:
        """Add multi-line output (respects ANSI codes)."""
        for line in text.strip().split("\n"):
            html = _ansi_to_html(line)
            self.output.append(
                f"<span style='color: {Colors.TEXT_SECONDARY}; font-family: {Fonts.MONO};'>"
                f"  {html}</span>"
            )
        self._enforce_scrollback()
        self._scroll_to_bottom()

    def add_divider(self) -> None:
        self.output.append(f"<hr style='border: 1px solid {Colors.BORDER_SUBTLE}; margin: 4px 0;'>")

    def clear(self) -> None:
        self.output.clear()
        self._line_count = 0

    # ── Private ────────────────────────────────────────────────────────

    def _add_entry(self, text: str, color: str, prefix: str = "›", bold: bool = False) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        weight = "bold" if bold else "normal"
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html = (
            f"<div style='margin-bottom: 2px; white-space: pre-wrap;'>"
            f"<span style='color: {Colors.TEXT_DIM}; font-size: 10px;'>{timestamp}</span>"
            f"<span style='color: {color}; margin-left: 6px;'>{prefix}</span>"
            f"<span style='color: {color}; font-weight: {weight}; margin-left: 6px;'>{escaped}</span>"
            f"</div>"
        )
        self.output.append(html)
        self._line_count += 1
        self._enforce_scrollback()
        self._scroll_to_bottom()

    def _enforce_scrollback(self) -> None:
        """Drop oldest lines if over the scrollback limit."""
        self._line_count += 1
        if self._line_count > self.MAX_LINES:
            cursor = self.output.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, 1)
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove the newline
            self._line_count -= 1

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(30, lambda: self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        ))

"""
Unified Main Window — the single composited Odus shell.
"""

from __future__ import annotations

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal

from odus.ui.theme import (
    Colors, Layout,
)
from odus.ui.mascot import MascotWidget
from odus.ui.components.header import HeaderBar
from odus.ui.components.sidebar import MascotSidebar
from odus.ui.components.input_bar import InputBar

logger = logging.getLogger(__name__)

class OdusMainWindow(QWidget):
    """
    Single composited window for the entire Odus experience.

    Layout:
      ┌── HeaderBar (drag + controls + tabs) ──────────────┐
      ├── Left Sidebar (mascot + status) ──┬── Content ────┤
      │                                    │ Chat/Terminal  │
      └────────────────────────────────────┴── InputBar ───┘
    """

    input_submitted = pyqtSignal(str)
    capture_requested = pyqtSignal()
    browse_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OdusMainWindow")
        self.setWindowTitle("Odus")

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.setMinimumSize(Layout.WINDOW_MIN_WIDTH, Layout.WINDOW_MIN_HEIGHT)
        self.resize(Layout.WINDOW_DEFAULT_WIDTH, Layout.WINDOW_DEFAULT_HEIGHT)

        # ── Outer container (provides background) ──
        self.outer = QFrame(self)
        self.outer.setObjectName("OuterFrame")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self.outer)

        main_layout = QVBoxLayout(self.outer)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ──
        self.header = HeaderBar()
        main_layout.addWidget(self.header)

        # ── Body (sidebar + content) ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sidebar
        self.sidebar = MascotSidebar()
        self.sidebar.capture_requested.connect(self.capture_requested.emit)
        self.sidebar.browse_requested.connect(self.browse_requested.emit)
        body.addWidget(self.sidebar)

        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")
        body.addWidget(self.content_stack, stretch=1)

        main_layout.addLayout(body, stretch=1)

        # ── Input bar ──
        self.input_bar = InputBar()
        self.input_bar.submitted.connect(self.input_submitted.emit)
        main_layout.addWidget(self.input_bar)

        # ── Tab switching ──
        self.header.tab_chat_btn.clicked.connect(lambda: self.switch_tab("chat"))
        self.header.tab_term_btn.clicked.connect(lambda: self.switch_tab("terminal"))

        self.header.toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)

        self._apply_style()

    # ── Public API ─────────────────────────────────────────────────────

    def toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def add_tab(self, name: str, widget: QWidget) -> None:
        """Add a content tab (e.g., 'chat', 'terminal')."""
        self.content_stack.addWidget(widget)
        widget.setProperty("tab_name", name)

    def switch_tab(self, name: str) -> None:
        """Switch to a named tab."""
        for i in range(self.content_stack.count()):
            w = self.content_stack.widget(i)
            if w.property("tab_name") == name:
                self.content_stack.setCurrentIndex(i)
                self.header.set_active_tab(name)
                return

    @property
    def mascot(self) -> MascotWidget:
        return self.sidebar.mascot

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() < 600:
            if not self.sidebar.isHidden():
                self.sidebar.hide()
        else:
            if self.sidebar.isHidden():
                self.sidebar.show()

    # ── Styling ────────────────────────────────────────────────────────

    def _apply_style(self):
        self.outer.setStyleSheet(f"""
            QFrame#OuterFrame {{
                background-color: {Colors.BG_PRIMARY};
            }}
        """)

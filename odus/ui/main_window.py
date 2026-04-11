"""
Unified Main Window — the single composited Odus shell.

Replaces the previous two-window architecture (MascotWindow + ChatInterface)
with one draggable, resizable window containing everything:

  ┌── Header (drag area + window controls) ────────────┐
  ├── Left Sidebar (mascot + status + quick actions) ───┤
  ├── Right Panel (tab stack: Chat / Terminal) ─────────┤
  └── Bottom Input Pill ────────────────────────────────┘
"""

from __future__ import annotations

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QStackedWidget, QGraphicsDropShadowEffect,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath, QRegion

from odus.ui.theme import (
    Colors, Fonts, FontSizes, Spacing, Radii,
    Gradients, Animations, GlassStyle, Layout,
)
from odus.ui.mascot import MascotWidget, MascotState

logger = logging.getLogger(__name__)


# ── Header Bar ─────────────────────────────────────────────────────────

class HeaderBar(QFrame):
    """
    Top header bar with logo, drag handle, and window controls.
    """

    close_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBar")
        self.setFixedHeight(Layout.HEADER_HEIGHT)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

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

        # Spacer label (also serves as drag area)
        self.drag_label = QLabel("")
        self.drag_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.drag_label.setCursor(Qt.CursorShape.SizeAllCursor)
        layout.addWidget(self.drag_label)

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

        # Separator
        layout.addSpacing(12)

        # Window control buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.min_btn = self._make_control_btn("─")
        self.max_btn = self._make_control_btn("□")
        self.close_btn = self._make_control_btn("✕", danger=True)

        self.min_btn.clicked.connect(self.minimize_requested.emit)
        self.max_btn.clicked.connect(self.maximize_requested.emit)
        self.close_btn.clicked.connect(self.close_requested.emit)

        btn_layout.addWidget(self.min_btn)
        btn_layout.addWidget(self.max_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

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

    def _make_control_btn(self, text: str, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hover_bg = Colors.DANGER if danger else Colors.BG_ELEVATED
        hover_color = "#ffffff" if danger else Colors.TEXT_PRIMARY
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                font-size: 13px;
                border-radius: 13px;
            }}
            QPushButton:hover {{
                color: {hover_color};
                background-color: {hover_bg};
            }}
        """)
        return btn

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#HeaderBar {{
                background: {Gradients.HEADER};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    # ── Drag handling ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            win = self.window()
            if win:
                win.move(win.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        """Double-click header to toggle maximize."""
        self.maximize_requested.emit()


# ── Sidebar ────────────────────────────────────────────────────────────

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


# ── Input Bar ──────────────────────────────────────────────────────────

class InputBar(QFrame):
    """
    Unified input pill at the bottom of the window.
    """

    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputBar")
        self.setFixedHeight(Layout.INPUT_HEIGHT + 20)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(0)

        # Pill container
        pill = QFrame()
        pill.setObjectName("InputPill")
        pill.setFixedHeight(Layout.INPUT_HEIGHT)
        pill_layout = QHBoxLayout(pill)
        pill_layout.setContentsMargins(16, 0, 8, 0)
        pill_layout.setSpacing(8)

        from PyQt6.QtWidgets import QLineEdit
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Odus something...")
        self.input_field.setFrame(False)
        self.input_field.setObjectName("InputField")
        self.input_field.returnPressed.connect(self._on_submit)

        self.send_btn = QPushButton("▶")
        self.send_btn.setFixedSize(34, 34)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.clicked.connect(self._on_submit)

        pill_layout.addWidget(self.input_field)
        pill_layout.addWidget(self.send_btn)

        layout.addWidget(pill)

        self._apply_style()

    def _on_submit(self):
        text = self.input_field.text().strip()
        if text:
            self.submitted.emit(text)
            self.input_field.clear()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#InputBar {{
                background-color: {Colors.BG_PRIMARY};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
            QFrame#InputPill {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 25px;
                border: 1px solid {Colors.BORDER};
            }}
            QLineEdit#InputField {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY};
                font-size: {FontSizes.MD}px;
                font-family: {Fonts.BODY};
                border: none;
            }}
            QPushButton#SendBtn {{
                background-color: {Colors.ACCENT};
                color: #000000;
                border-radius: 17px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton#SendBtn:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
        """)


# ── Main Window ────────────────────────────────────────────────────────

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

        # Frameless + transparent for custom shape
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setMinimumSize(Layout.WINDOW_MIN_WIDTH, Layout.WINDOW_MIN_HEIGHT)
        self.resize(Layout.WINDOW_DEFAULT_WIDTH, Layout.WINDOW_DEFAULT_HEIGHT)

        # ── Outer container (provides rounded corners + background) ──
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
        self.header.close_requested.connect(self.close)
        self.header.minimize_requested.connect(self.showMinimized)
        self.header.maximize_requested.connect(self._toggle_maximize)
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

        # ── Window shadow ──
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        self.outer.setGraphicsEffect(shadow)

        # ── Tab switching ──
        self.header.tab_chat_btn.clicked.connect(lambda: self.switch_tab("chat"))
        self.header.tab_term_btn.clicked.connect(lambda: self.switch_tab("terminal"))

        self._apply_style()

        # Resize handle state
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self.setMouseTracking(True)

    # ── Public API ─────────────────────────────────────────────────────

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

    # ── Window controls ────────────────────────────────────────────────

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ── Resize handling (manual, since frameless) ──────────────────────

    _EDGE_MARGIN = 8

    def _detect_edge(self, pos: QPoint) -> str | None:
        """Detect which edge/corner the mouse is near."""
        rect = self.rect()
        m = self._EDGE_MARGIN

        on_left = pos.x() <= m
        on_right = pos.x() >= rect.width() - m
        on_top = pos.y() <= m
        on_bottom = pos.y() >= rect.height() - m

        if on_bottom and on_right:
            return "bottom-right"
        if on_bottom and on_left:
            return "bottom-left"
        if on_top and on_right:
            return "top-right"
        if on_bottom:
            return "bottom"
        if on_right:
            return "right"
        if on_left:
            return "left"
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._detect_edge(event.pos())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()

    def mouseMoveEvent(self, event):
        # Update cursor shape based on edge proximity
        if not self._resize_edge:
            edge = self._detect_edge(event.pos())
            cursors = {
                "bottom-right": Qt.CursorShape.SizeFDiagCursor,
                "bottom-left": Qt.CursorShape.SizeBDiagCursor,
                "top-right": Qt.CursorShape.SizeBDiagCursor,
                "bottom": Qt.CursorShape.SizeVerCursor,
                "right": Qt.CursorShape.SizeHorCursor,
                "left": Qt.CursorShape.SizeHorCursor,
            }
            if edge and edge in cursors:
                self.setCursor(cursors[edge])
            else:
                self.unsetCursor()
            return

        # Perform resize
        if event.buttons() & Qt.MouseButton.LeftButton and self._resize_start_pos:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            geo = self._resize_start_geo
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            if "right" in self._resize_edge:
                new_w = max(min_w, geo.width() + delta.x())
                self.resize(new_w, self.height())
            if "left" in self._resize_edge:
                new_w = max(min_w, geo.width() - delta.x())
                if new_w > min_w:
                    self.setGeometry(geo.x() + delta.x(), geo.y(), new_w, geo.height())
            if "bottom" in self._resize_edge:
                new_h = max(min_h, geo.height() + delta.y())
                self.resize(self.width(), new_h)

    def mouseReleaseEvent(self, event):
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self.unsetCursor()

    # ── Styling ────────────────────────────────────────────────────────

    def _apply_style(self):
        self.outer.setStyleSheet(f"""
            QFrame#OuterFrame {{
                background-color: {Colors.BG_PRIMARY};
                border-radius: {Radii.WINDOW}px;
                border: 1px solid {Colors.BORDER};
            }}
        """)

"""
Standard 16:9 Chat Window (v2) — Editorial Obsidian Style.
Supports collapsing into a floating draggable mascot.

On GNOME Wayland, self.geometry() / self.pos() always returns (0, 0) for the
window position. We therefore track every position ourselves and feed those
tracked positions into QPropertyAnimation start/end values so that animations
remain smooth and positions remain correct.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QWidget, QMainWindow, QApplication,
    QLabel, QPushButton, QMenu
)
from PyQt6.QtCore import (
    Qt, QSize, QPoint, QRect,
    QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import QPixmap, QIcon

from odus.ui_v2.theme import (
    Colors, Layout, Spacing, Radii, Fonts
)
from odus.ui_v2.components.header import SidebarHeaderV2
from odus.ui_v2.components.chat_history import ChatHistoryV2
from odus.ui_v2.components.input_bar import InputBarV2
from odus.ui_v2.components.ghost_terminal import GhostTerminalV2

import logging

logger = logging.getLogger(__name__)

MASCOT_SIZE = 64  # px — floating mascot diameter


class ChatWindowV2(QMainWindow):
    """
    Standard window with collapse-to-mascot support.
    × collapses into a draggable floating mascot.
    ⏻ quits the application.
    """

    def __init__(self):
        super().__init__()

        # ── Window flags: frameless + always-on-top ──
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setMinimumSize(640, 360)
        self.resize(Layout.WINDOW_INITIAL_WIDTH, Layout.WINDOW_INITIAL_HEIGHT)

        # ── Position tracking ──
        # On Wayland, self.pos()/self.geometry() always return (0,0).
        # We track positions manually so animations and drag work correctly.
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        # Where the expanded window is (tracked manually)
        self._window_pos = QPoint(
            geo.x() + (geo.width() - Layout.WINDOW_INITIAL_WIDTH) // 2,
            geo.y() + (geo.height() - Layout.WINDOW_INITIAL_HEIGHT) // 2,
        )

        # Where the collapsed mascot lives (sticky — only changes via drag)
        self._mascot_pos = QPoint(
            geo.x() + geo.width() - MASCOT_SIZE - 16,
            geo.y() + (geo.height() - MASCOT_SIZE) // 2,
        )

        # ── State ──
        self._is_expanded = True
        self._saved_window_size: QSize | None = None
        self._drag_pos: QPoint | None = None  # offset for mascot drag
        self._drag_start_pos: QPoint | None = None  # detect click vs drag
        self._window_drag_pos: QPoint | None = None  # offset for window drag

        # ── Central Widget ──
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # ── Full Window Panel ──
        self.window_panel = QFrame()
        self.window_panel.setObjectName("WindowPanel")
        panel_layout = QVBoxLayout(self.window_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # Header
        self.header = SidebarHeaderV2()
        self.header.close_clicked.connect(self.collapse)
        self.header.quit_requested.connect(self._quit_app)
        self.header.setStyleSheet(
            f"background-color: {Colors.BG_LEVEL_1}; border-bottom: 1px solid {Colors.BORDER_GHOST};"
        )

        # Content Area (Horizontal for a wide window)
        self.content_frame = QFrame()
        self.content_layout = QHBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        self.content_layout.setSpacing(Spacing.MD)

        self.chat_history = ChatHistoryV2()
        self.terminal = GhostTerminalV2()  # kept for API compat, not shown
        self.terminal.setVisible(False)
        self.content_layout.addWidget(self.chat_history, stretch=1)

        self.input_bar = InputBarV2()

        panel_layout.addWidget(self.header)
        panel_layout.addWidget(self.content_frame, stretch=1)
        panel_layout.addWidget(self.input_bar)

        # ── Floating Mascot (shown when collapsed) ──
        self.mascot_bubble = QFrame()
        self.mascot_bubble.setObjectName("MascotBubble")
        self.mascot_bubble.setFixedSize(MASCOT_SIZE, MASCOT_SIZE)
        self.mascot_bubble.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mascot_bubble.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mascot_bubble.customContextMenuRequested.connect(self._show_mascot_menu)

        mascot_layout = QVBoxLayout(self.mascot_bubble)
        mascot_layout.setContentsMargins(0, 0, 0, 0)
        mascot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mascot_label = QLabel("🦉")
        self.mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot_label.setStyleSheet(
            f"color: {Colors.PRIMARY}; font-size: 32px; background: transparent;"
        )
        self.mascot_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        pixmap = QPixmap("assets/mascot_idle.png")
        if not pixmap.isNull():
            self.mascot_label.setPixmap(
                pixmap.scaled(
                    MASCOT_SIZE - 16, MASCOT_SIZE - 16,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.mascot_label.setText("")

        mascot_layout.addWidget(self.mascot_label)
        self.mascot_bubble.mousePressEvent = self._mascot_press
        self.mascot_bubble.mouseMoveEvent = self._mascot_move
        self.mascot_bubble.mouseReleaseEvent = self._mascot_release

        # ── Assemble root layout ──
        self.root_layout.addWidget(self.window_panel)
        self.root_layout.addWidget(self.mascot_bubble)

        # Start expanded
        self.mascot_bubble.setVisible(False)
        self.window_panel.setVisible(True)

        # ── Animation ──
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(Layout.TRANSITION_SPEED)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._apply_style()
        # Position the window at the tracked location
        self.move(self._window_pos)

    # ── Styling ─────────────────────────────────────────────────────────

    def _apply_style(self):
        self.window_panel.setStyleSheet(f"""
            QFrame#WindowPanel {{
                background-color: {Colors.BG_BASE};
                border: 1px solid {Colors.BORDER_GHOST};
                border-radius: {Radii.LG}px;
            }}
        """)
        self.mascot_bubble.setStyleSheet(f"""
            QFrame#MascotBubble {{
                background: {Colors.BG_LEVEL_1};
                border-radius: {MASCOT_SIZE // 2}px;
                border: 2px solid {Colors.PRIMARY};
            }}
            QFrame#MascotBubble:hover {{
                background: {Colors.BG_LEVEL_2};
                border-color: {Colors.PRIMARY};
            }}
        """)

    def _center_on_screen(self):
        """Calculate centered position and move there. Updates _window_pos."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self._window_pos = QPoint(x, y)
            self.move(x, y)

    # ── Collapse / Expand ───────────────────────────────────────────────

    def _unlock_size(self):
        """Remove fixed size constraints so animations can work."""
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

    def collapse(self):
        """Collapse the window into a floating mascot bubble at the sticky position."""
        if not self._is_expanded:
            return
        self._is_expanded = False
        self._saved_window_size = QSize(self.width(), self.height())

        # Build start/end rects from our tracked positions (not self.geometry())
        start_rect = QRect(
            self._window_pos.x(), self._window_pos.y(),
            self.width(), self.height(),
        )
        end_rect = QRect(
            self._mascot_pos.x(), self._mascot_pos.y(),
            MASCOT_SIZE, MASCOT_SIZE,
        )

        logger.info("COLLAPSE: start=%s → end=%s", start_rect, end_rect)

        self._unlock_size()
        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        self.anim.finished.connect(self._on_collapse_done)
        self.anim.start()

    def _on_collapse_done(self):
        if not self._is_expanded:
            self.window_panel.setVisible(False)
            self.mascot_bubble.setVisible(True)
            self.setFixedSize(MASCOT_SIZE, MASCOT_SIZE)
            self.move(self._mascot_pos)
        try:
            self.anim.finished.disconnect(self._on_collapse_done)
        except Exception:
            pass

    def expand(self):
        """Expand from floating mascot back to full window."""
        if self._is_expanded:
            return
        self._is_expanded = True

        self.mascot_bubble.setVisible(False)
        self.window_panel.setVisible(True)

        w = self._saved_window_size.width() if self._saved_window_size else Layout.WINDOW_INITIAL_WIDTH
        h = self._saved_window_size.height() if self._saved_window_size else Layout.WINDOW_INITIAL_HEIGHT

        # Recalculate centered position for the expanded window
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        cx = geo.x() + (geo.width() - w) // 2
        cy = geo.y() + (geo.height() - h) // 2
        self._window_pos = QPoint(cx, cy)

        # Build start/end rects from our tracked positions
        start_rect = QRect(
            self._mascot_pos.x(), self._mascot_pos.y(),
            MASCOT_SIZE, MASCOT_SIZE,
        )
        end_rect = QRect(cx, cy, w, h)

        logger.info("EXPAND: start=%s → end=%s", start_rect, end_rect)

        self._unlock_size()
        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        self.anim.finished.connect(self._on_expand_done)
        self.anim.start()

    def _on_expand_done(self):
        if self._is_expanded:
            w = self._saved_window_size.width() if self._saved_window_size else Layout.WINDOW_INITIAL_WIDTH
            h = self._saved_window_size.height() if self._saved_window_size else Layout.WINDOW_INITIAL_HEIGHT
            self.setMinimumSize(640, 360)
            self.setMaximumSize(16777215, 16777215)
            self.resize(w, h)
            self.move(self._window_pos)
        try:
            self.anim.finished.disconnect(self._on_expand_done)
        except Exception:
            pass

    # ── Mascot drag ─────────────────────────────────────────────────────

    def _mascot_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Use tracked _mascot_pos for offset (self.frameGeometry() returns (0,0) on Wayland)
            self._drag_pos = event.globalPosition().toPoint() - self._mascot_pos
            self._drag_start_pos = event.globalPosition().toPoint()
            event.accept()

    def _mascot_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            self._mascot_pos = new_pos  # continuously track sticky position
            event.accept()

    def _mascot_release(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_pos is not None:
                total_moved = 0
                if self._drag_start_pos is not None:
                    total_moved = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
                self._drag_pos = None
                self._drag_start_pos = None

                logger.info("MASCOT_RELEASE: total_moved=%s, _mascot_pos=(%s,%s)",
                            total_moved, self._mascot_pos.x(), self._mascot_pos.y())
                if total_moved < 8:
                    self.expand()
                # else: drag — position already saved in _mascot_move
            event.accept()

    def _show_mascot_menu(self, pos):
        """Context menu on the floating mascot."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.BG_LEVEL_1};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_GHOST};
                border-radius: {Radii.MD}px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: {Radii.SM}px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.BG_LEVEL_2};
                color: {Colors.PRIMARY};
            }}
        """)

        expand_action = menu.addAction("Open Odus")
        expand_action.triggered.connect(self.expand)
        menu.addSeparator()
        quit_action = menu.addAction("Quit Odus")
        quit_action.triggered.connect(self._quit_app)
        menu.exec(self.mascot_bubble.mapToGlobal(pos))

    # ── Window dragging (header area) ───────────────────────────────────

    def mousePressEvent(self, event):
        if self._is_expanded and event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 60:
                # Use widget-local offset (doesn't depend on Wayland pos reporting)
                self._window_drag_pos = event.position().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._window_drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._window_drag_pos
            self.move(new_pos)
            self._window_pos = new_pos  # track the window position
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._window_drag_pos = None
        super().mouseReleaseEvent(event)

    # ── Public API ──────────────────────────────────────────────────────

    def _quit_app(self):
        """Cleanly exit the application."""
        QApplication.quit()

    def set_mascot_state(self, state: str):
        """Update mascot icons based on state (idle, thinking, success, error)."""
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

        # Update Header Mascot
        self.header.mascot_icon.setPixmap(
            pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        self.header.mascot_icon.setText("")

        # Update Floating Mascot
        self.mascot_label.setPixmap(
            pixmap.scaled(
                MASCOT_SIZE - 16, MASCOT_SIZE - 16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.mascot_label.setText("")

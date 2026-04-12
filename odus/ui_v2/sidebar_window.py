"""
Main Sidebar Window (v2) — Editorial Obsidian Style.
"""

from __future__ import annotations

import sys
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QWidget, QMainWindow, QApplication, QGraphicsBlurEffect, QLabel, QMenu, QStackedWidget, QPushButton
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QScreen, QAction, QPixmap

from odus.ui_v2.theme import (
    Colors, Layout, Spacing, Radii, Fonts
)
from odus.ui_v2.components.header import SidebarHeaderV2
from odus.ui_v2.components.chat_history import ChatHistoryV2
from odus.ui_v2.components.input_bar import InputBarV2
from odus.ui_v2.components.ghost_terminal import GhostTerminalV2

class SidebarWindowV2(QMainWindow):
    """
    Constant sidebar widget.
    Minimized when not in use, expanded on the right side when open.
    """

    def __init__(self):
        super().__init__()

        # Window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Screen tracking
        self.screen = QApplication.primaryScreen()
        self.screen.geometryChanged.connect(self._on_screen_geometry_changed)

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # Main layout is Horizontal, but we want the PANEL on the RIGHT
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Add a stretch on the LEFT to push everything to the RIGHT
        self.main_layout.addStretch(1)

        # The Sidebar Panel
        self.panel = QFrame()
        self.panel.setObjectName("SidebarPanel")
        self.panel.setFixedWidth(Layout.SIDEBAR_WIDTH_EXPANDED) # Fixed panel width
        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        self.panel_layout.setSpacing(0)

        self.header = SidebarHeaderV2()
        self.header.close_clicked.connect(self.collapse)
        self.header.quit_requested.connect(self._quit_app)
        
        # Content Area (Merged Chat and Terminal)
        self.chat_history = ChatHistoryV2()
        self.terminal = GhostTerminalV2()
        # Set a reasonable height for terminal when merged
        self.terminal.setFixedHeight(200) 
        self.terminal.setVisible(False) # Hide until needed

        self.input_bar = InputBarV2()

        self.panel_layout.addWidget(self.header)
        self.panel_layout.addWidget(self.chat_history, stretch=1)
        self.panel_layout.addWidget(self.terminal)
        self.panel_layout.addWidget(self.input_bar)

        # The Trigger Node (Mascot Node)
        self.trigger = QFrame()
        self.trigger.setObjectName("MascotNode")
        self.trigger.setFixedSize(Layout.NODE_SIZE + 16, Layout.NODE_SIZE + 16)
        self.trigger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trigger.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trigger.customContextMenuRequested.connect(self._show_trigger_menu)
        
        trigger_layout = QVBoxLayout(self.trigger)
        trigger_layout.setContentsMargins(0, 0, 0, 0)
        trigger_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.trigger_icon = QLabel("🦉")
        self.trigger_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trigger_icon.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 32px; background: transparent;")
        
        # Load mascot image
        pixmap = QPixmap("assets/mascot_idle.png")
        if not pixmap.isNull():
            self.trigger_icon.setPixmap(pixmap.scaled(Layout.NODE_SIZE, Layout.NODE_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.trigger_icon.setText("")
            
        trigger_layout.addWidget(self.trigger_icon)
        self.trigger.mousePressEvent = self._on_trigger_clicked

        self.main_layout.addWidget(self.panel)
        self.main_layout.addWidget(self.trigger)

        # Animations
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(Layout.TRANSITION_SPEED)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Initial State: Start Collapsed
        self._is_expanded = False
        self._apply_style()
        self.panel.setVisible(False)
        self.trigger.setVisible(True)

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
        self.header.mascot_icon.setPixmap(pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.header.mascot_icon.setText("")

        # Update Trigger Mascot
        self.trigger_icon.setPixmap(pixmap.scaled(Layout.NODE_SIZE, Layout.NODE_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.trigger_icon.setText("")

    def showEvent(self, event):
        """Handle initial docking when window is shown."""
        super().showEvent(event)
        self._update_geometry(animate=False)

    def _quit_app(self):
        """Cleanly exit the application."""
        QApplication.quit()

    def _show_trigger_menu(self, pos):
        """Show context menu on the trigger."""
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
        
        expand_action = menu.addAction("Expand Sidebar")
        expand_action.triggered.connect(self.expand)
        
        menu.addSeparator()
        
        quit_action = menu.addAction("Quit Odus")
        quit_action.triggered.connect(self._quit_app)
        
        menu.exec(self.trigger.mapToGlobal(pos))

    def _on_trigger_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.expand()
        elif event.button() == Qt.MouseButton.RightButton:
            # Context menu is handled by customContextMenuRequested
            pass

    def _apply_style(self):
        self.panel.setStyleSheet(f"""
            QFrame#SidebarPanel {{
                background-color: {Colors.BG_BASE};
                border-left: 1px solid {Colors.BORDER_GHOST};
            }}
        """)
        
        self.trigger.setStyleSheet(f"""
            QFrame#MascotNode {{
                background: {Colors.BG_LEVEL_1};
                border-radius: {(Layout.NODE_SIZE + 16) // 2}px;
                border: 2px solid {Colors.PRIMARY};
            }}
            QFrame#MascotNode:hover {{
                background: {Colors.BG_LEVEL_2};
                border-color: {Colors.PRIMARY};
            }}
        """)

    def _on_screen_geometry_changed(self, geometry):
        """Handle screen resolution changes."""
        self._update_geometry(animate=False)

    def expand(self):
        """Slide out the sidebar."""
        self._is_expanded = True
        self.panel.setVisible(True)
        self.trigger.setVisible(False)
        self._update_geometry(animate=True)
        self.anim.finished.connect(self._on_expand_finished)

    def _on_expand_finished(self):
        """Finalize expand state."""
        if self._is_expanded:
            self.setFixedWidth(Layout.SIDEBAR_WIDTH_EXPANDED)
        try:
            self.anim.finished.disconnect(self._on_expand_finished)
        except:
            pass

    def collapse(self):
        """Slide in and show the trigger."""
        self._is_expanded = False
        # Panel remains visible so we can animate the window shrinking to the right
        self.panel.setVisible(True)
        self.trigger.setVisible(False)
        self._update_geometry(animate=True)
        self.anim.finished.connect(self._on_collapse_finished)

    def _on_collapse_finished(self):
        """Finalize collapse state after animation."""
        if not self._is_expanded:
            self.panel.setVisible(False)
            self.trigger.setVisible(True)
            self._update_geometry(animate=False)
        try:
            self.anim.finished.disconnect(self._on_collapse_finished)
        except:
            pass

    def _update_geometry(self, animate: bool = True):
        """Calculate and set the docked geometry."""
        screen_geo = self.screen.availableGeometry()
        
        if self._is_expanded:
            width = Layout.SIDEBAR_WIDTH_EXPANDED
            height = screen_geo.height()
            y = screen_geo.top()
        else:
            width = Layout.NODE_SIZE + 32 # Mascot + padding/shadow room
            height = Layout.NODE_SIZE + 32
            y = screen_geo.top() + (screen_geo.height() - height) // 2
            
        # docking precisely to the rightmost pixel
        x = screen_geo.x() + screen_geo.width() - width
        target_rect = QRect(x, y, width, height)
        
        if animate:
            self.anim.stop()
            # Remove constraints to allow animation
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(target_rect)
            self.anim.start()
        else:
            self.setGeometry(target_rect)
            # Lock size after positioning to prevent WM interference
            self.setFixedWidth(width)
            self.setFixedHeight(height)

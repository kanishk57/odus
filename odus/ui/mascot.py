"""
Mascot State Machine — controls the mascot's visual state and animations in PyQt6.
"""

import logging
from enum import Enum
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from odus.ui.theme import Colors, FontSizes, Radii

logger = logging.getLogger(__name__)


class MascotState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


MASCOT_DISPLAY = {
    MascotState.IDLE: "🦉",
    MascotState.THINKING: "🔍",
    MascotState.SUCCESS: "✅",
    MascotState.ERROR: "❌",
    MascotState.WARNING: "⚠️",
}

MASCOT_COLORS = {
    MascotState.IDLE: Colors.TEXT_SECONDARY,
    MascotState.THINKING: Colors.ACCENT,
    MascotState.SUCCESS: Colors.SUCCESS,
    MascotState.ERROR: Colors.DANGER,
    MascotState.WARNING: Colors.WARNING,
}


class MascotWindow(QWidget):
    """
    Floating mascot widget that stays on top and is fully transparent.
    """
    
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = MascotState.IDLE

        # Window Setup (Frameless, Transparent, Always on Top)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Prevents showing in taskbar optionally
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Bubble Container
        self.container = QWidget()
        self.container.setObjectName("MascotContainer")
        self.container.setFixedSize(120, 120)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 2)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot Emoji
        self.icon_label = QLabel(MASCOT_DISPLAY[self._state])
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet(f"font-size: 60px; background: transparent;")
        
        container_layout.addWidget(self.icon_label)
        self.layout.addWidget(self.container)

        self.set_state(MascotState.IDLE)
        
        # Determine position (e.g., bottom right)
        # We will set position from app.py

    def mousePressEvent(self, event):
        """Detect clicks to expand UI and initiate drag context."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._window_start_pos = self.frameGeometry().topLeft()
            self._is_dragging = False
            
    def mouseMoveEvent(self, event):
        """Allow dragging the frameless window naturally across the desktop."""
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_start_pos'):
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            if delta.manhattanLength() > 5:
                # We moved enough to be a drag, not a click
                self._is_dragging = True
                self.move(self._window_start_pos + delta)

    def mouseReleaseEvent(self, event):
        """Trigger the clicked signal if it was a distinct static click."""
        if event.button() == Qt.MouseButton.LeftButton:
            if not getattr(self, '_is_dragging', False):
                self.clicked.emit()
            self._is_dragging = False

    @property
    def state(self) -> MascotState:
        return self._state

    def set_state(self, state: MascotState) -> None:
        """Update mascot appearance."""
        self._state = state
        self.icon_label.setText(MASCOT_DISPLAY[state])
        
        color = MASCOT_COLORS[state]
        radius = Radii.LG
        
        # Update styling
        self.container.setStyleSheet(f"""
            QWidget#MascotContainer {{
                background-color: {Colors.BG_SECONDARY};
                border: 2px solid {color};
                border-radius: {radius}px;
            }}
        """)

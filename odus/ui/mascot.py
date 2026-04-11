"""
Mascot State Machine — controls the mascot's visual state and animations in PyQt6.
"""

import logging
from enum import Enum
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation
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

        # 1. Outer Container for the Shadow
        self.shadow_container = QWidget()
        self.shadow_container.setFixedSize(120, 120)
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 120))
        self.shadow.setOffset(0, 2)
        self.shadow_container.setGraphicsEffect(self.shadow)
        
        shadow_layout = QVBoxLayout(self.shadow_container)
        shadow_layout.setContentsMargins(0, 0, 0, 0)

        # 2. Inner Container for the Pulsing Opacity
        self.container = QWidget()
        self.container.setObjectName("MascotContainer")
        self.opacity_effect = QGraphicsOpacityEffect(self.container)
        self.container.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(1200)
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 0.4)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setLoopCount(-1)

        container_layout = QVBoxLayout(self.container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot Emoji
        self.icon_label = QLabel(MASCOT_DISPLAY[self._state])
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet(f"font-size: 60px; background: transparent;")
        
        container_layout.addWidget(self.icon_label)
        shadow_layout.addWidget(self.container)
        self.layout.addWidget(self.shadow_container)

        self.set_state(MascotState.IDLE)

    def set_state(self, state: MascotState) -> None:
        """Update mascot appearance and trigger animations."""
        self._state = state
        self.icon_label.setText(MASCOT_DISPLAY[state])
        
        # Reset animation
        self.pulse_anim.stop()
        self.opacity_effect.setOpacity(1.0)

        if state == MascotState.THINKING:
            self.pulse_anim.start()

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

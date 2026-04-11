"""
Mascot Widget — embeddable animated mascot for the unified sidebar.

No longer a standalone window. Now a QWidget that lives inside
OdusMainWindow's sidebar, with animated state transitions.
"""

import logging
import os
from enum import Enum

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QColor, QPixmap

from odus.ui.theme import Colors, Animations, Layout

logger = logging.getLogger(__name__)


class MascotState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

MASCOT_DISPLAY = {
    MascotState.IDLE: os.path.join(ASSET_DIR, "mascot_idle.png"),
    MascotState.THINKING: os.path.join(ASSET_DIR, "mascot_thinking.png"),
    MascotState.SUCCESS: os.path.join(ASSET_DIR, "mascot_success.png"),
    MascotState.ERROR: os.path.join(ASSET_DIR, "mascot_error.png"),
    MascotState.WARNING: os.path.join(ASSET_DIR, "mascot_warning.png"),
}

MASCOT_RING_COLORS = {
    MascotState.IDLE: Colors.TEXT_DIM,
    MascotState.THINKING: Colors.ACCENT,
    MascotState.SUCCESS: Colors.SUCCESS,
    MascotState.ERROR: Colors.DANGER,
    MascotState.WARNING: Colors.WARNING,
}


class MascotWidget(QWidget):
    """
    Embeddable mascot widget with animated state machine.

    Lives inside the sidebar of OdusMainWindow. Shows the owl mascot
    with a glowing ring that changes color based on state.

    Animations:
      - THINKING: continuous pulse (opacity 0.4→1.0→0.4)
      - SUCCESS: bounce (scale 1.0→1.15→1.0)
      - State change: smooth opacity cross-fade
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = MascotState.IDLE
        self.setFixedSize(Layout.MASCOT_SIZE + 20, Layout.MASCOT_SIZE + 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Container for ring + image
        self.container = QWidget()
        self.container.setObjectName("MascotRing")
        self.container.setFixedSize(Layout.MASCOT_SIZE, Layout.MASCOT_SIZE)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mascot image
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent;")
        container_layout.addWidget(self.icon_label)

        layout.addWidget(self.container)

        # ── Opacity effect for cross-fade ──
        self.opacity_effect = QGraphicsOpacityEffect(self.container)
        self.container.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        # ── Pulse animation (THINKING) ──
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(Animations.PULSE)
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 0.4)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setLoopCount(-1)

        # ── Bounce animation (SUCCESS) ──
        self.bounce_anim = QPropertyAnimation(self.container, b"minimumSize")
        self.bounce_anim.setDuration(Animations.FAST)
        self.bounce_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        self.bounce_anim_back = QPropertyAnimation(self.container, b"minimumSize")
        self.bounce_anim_back.setDuration(Animations.NORMAL)
        self.bounce_anim_back.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # ── Drop shadow for glow ──
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(20)
        self.glow.setColor(QColor(Colors.ACCENT))
        self.glow.setOffset(0, 0)
        # Don't apply to container (conflicts with opacity effect)
        # Apply to this widget instead
        self.setGraphicsEffect(self.glow)

        self.set_state(MascotState.IDLE)

    def set_state(self, state: MascotState) -> None:
        """Update mascot appearance with smooth transitions."""
        self._state = state

        # Load new mascot image
        img_path = MASCOT_DISPLAY.get(state, MASCOT_DISPLAY[MascotState.IDLE])
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                Layout.MASCOT_SIZE - 16, Layout.MASCOT_SIZE - 16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon_label.setPixmap(scaled)

        # Stop previous animations
        self.pulse_anim.stop()
        self.opacity_effect.setOpacity(1.0)

        # Update ring color
        ring_color = MASCOT_RING_COLORS.get(state, Colors.TEXT_DIM)
        self.container.setStyleSheet(f"""
            QWidget#MascotRing {{
                background-color: {Colors.BG_SECONDARY};
                border: 2px solid {ring_color};
                border-radius: {Layout.MASCOT_SIZE // 2}px;
            }}
        """)

        # Update glow color
        glow_color = QColor(ring_color)
        glow_color.setAlpha(80)
        self.glow.setColor(glow_color)

        # State-specific animations
        if state == MascotState.THINKING:
            self.glow.setBlurRadius(30)
            self.pulse_anim.start()

        elif state == MascotState.SUCCESS:
            self.glow.setBlurRadius(25)
            # Brief bounce: grow then shrink
            self._do_bounce()

        elif state == MascotState.ERROR:
            self.glow.setBlurRadius(25)

        else:
            self.glow.setBlurRadius(15)

    def _do_bounce(self) -> None:
        """Quick scale bounce animation for success state using QPropertyAnimation."""
        original_size = Layout.MASCOT_SIZE
        big_size = int(original_size * 1.15)
        
        # Grow
        self.bounce_anim.setStartValue(QSize(original_size, original_size))
        self.bounce_anim.setEndValue(QSize(big_size, big_size))
        
        # Shrink
        self.bounce_anim_back.setStartValue(QSize(big_size, big_size))
        self.bounce_anim_back.setEndValue(QSize(original_size, original_size))
        
        try:
            self.bounce_anim.finished.disconnect(self.bounce_anim_back.start)
        except TypeError:
            pass
        
        self.bounce_anim.finished.connect(self.bounce_anim_back.start)
        self.bounce_anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    @property
    def state(self) -> MascotState:
        return self._state

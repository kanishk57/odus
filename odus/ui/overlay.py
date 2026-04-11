"""
Action Overlay — transparent fullscreen window that highlights where
the agent is about to act on the user's desktop.

Shows a pulsing glowing rectangle at the target coordinates before
the agent clicks, types, or interacts with a GUI element.
"""

import logging
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from odus.ui.theme import Colors, Fonts, FontSizes

logger = logging.getLogger(__name__)


class ActionOverlay(QWidget):
    """
    Transparent fullscreen overlay that draws visual cues on the screen.

    Features:
      - Pulsing rectangle highlight at target coordinates
      - Label with the action description
      - Crosshair at click target
      - Auto-dismiss after a timeout

    Usage:
        overlay = ActionOverlay()
        overlay.show_highlight(x=320, y=450, w=120, h=40,
                               label="Save button", duration_ms=3000)
        overlay.show_crosshair(x=320, y=450, label="Click here")
        overlay.dismiss()
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Fullscreen, always on top, transparent, click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Cover the entire screen
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        # Highlight state
        self._highlight_rect: QRect | None = None
        self._crosshair_pos: tuple[int, int] | None = None
        self._ghost_cursor_pos: tuple[int, int] | None = None
        self._is_typing: bool = False
        self._label_text: str = ""
        self._pulse_alpha: int = 180
        self._pulse_increasing: bool = False

        # Pulse animation timer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

    # ── Public API ─────────────────────────────────────────────────────

    def show_highlight(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str = "",
        duration_ms: int = 4000,
    ) -> None:
        """
        Show a pulsing rectangle highlight on the screen.

        Args:
            x, y: Top-left corner of the highlight rectangle.
            w, h: Width and height of the highlight.
            label: Text label to show near the highlight.
            duration_ms: How long to show the highlight (0 = forever).
        """
        # Ensure overlay covers current screen geometry
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self._highlight_rect = QRect(x, y, w, h)
        self._crosshair_pos = None
        self._label_text = label
        self._pulse_alpha = 180

        self._pulse_timer.start(50)  # ~20fps pulse

        if duration_ms > 0:
            self._dismiss_timer.start(duration_ms)

        self.show()
        self.raise_()
        self.update()

        logger.debug("Overlay highlight shown at (%d, %d, %d, %d): %s", x, y, w, h, label)

    def show_crosshair(
        self,
        x: int,
        y: int,
        label: str = "",
        duration_ms: int = 3000,
    ) -> None:
        """
        Show a crosshair + pulse at a specific point (for click targets).
        """
        self._ghost_cursor_pos = (x, y)
        # Create a small highlight rect around the crosshair point
        self.show_highlight(
            x=x - 20, y=y - 20, w=40, h=40,
            label=label, duration_ms=duration_ms,
        )
        self._crosshair_pos = (x, y)
        self.update()

    def set_ghost_cursor(self, x: int | None, y: int | None, is_typing: bool = False) -> None:
        """Update the position of the software-rendered ghost cursor."""
        if x is None or y is None:
            self._ghost_cursor_pos = None
        else:
            self._ghost_cursor_pos = (x, y)
        self._is_typing = is_typing
        
        if self._ghost_cursor_pos:
            self.show()
            self.raise_()
        self.update()

    def dismiss(self) -> None:
        """Hide the overlay and reset state."""
        self._pulse_timer.stop()
        self._dismiss_timer.stop()
        self._highlight_rect = None
        self._crosshair_pos = None
        self._label_text = ""
        self.hide()

    # ── Painting ───────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._highlight_rect:
            self._draw_highlight(painter)

        if self._crosshair_pos:
            self._draw_crosshair(painter)

        if self._ghost_cursor_pos:
            self._draw_ghost_cursor(painter)

        if self._label_text and self._highlight_rect:
            self._draw_label(painter)

        painter.end()

    def _draw_ghost_cursor(self, painter: QPainter) -> None:
        """Draw a stylized software cursor representing Odus's focus."""
        if not self._ghost_cursor_pos:
            return

        x, y = self._ghost_cursor_pos
        accent = QColor(Colors.ACCENT)
        
        # Outer glow ring
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(accent.red(), accent.green(), accent.blue(), 60)))
        painter.drawEllipse(x - 12, y - 12, 24, 24)
        
        # Inner dot
        painter.setBrush(QBrush(accent))
        painter.drawEllipse(x - 4, y - 4, 8, 8)
        
        # Typing indicator
        if self._is_typing:
            font = QFont(Fonts.MONO, FontSizes.XS, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(Colors.TEXT_PRIMARY))
            # Floating "..." or "⌨"
            painter.drawText(x + 12, y - 12, "⌨ TYPING...")

    def _draw_highlight(self, painter: QPainter) -> None:
        """Draw a pulsing glowing rectangle."""
        rect = self._highlight_rect
        if not rect:
            return

        accent = QColor(Colors.ACCENT)
        alpha = self._pulse_alpha

        # Outer glow
        glow_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), alpha // 2))
        glow_pen.setWidth(6)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 8, 8)

        # Main border
        main_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), alpha))
        main_pen.setWidth(3)
        painter.setPen(main_pen)

        # Semi-transparent fill
        fill = QColor(accent.red(), accent.green(), accent.blue(), alpha // 6)
        painter.setBrush(QBrush(fill))
        painter.drawRoundedRect(rect, 6, 6)

    def _draw_crosshair(self, painter: QPainter) -> None:
        """Draw crosshair lines at the click target."""
        if not self._crosshair_pos:
            return

        x, y = self._crosshair_pos
        accent = QColor(Colors.ACCENT)
        pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), self._pulse_alpha))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        # Horizontal line
        painter.drawLine(x - 30, y, x + 30, y)
        # Vertical line
        painter.drawLine(x, y - 30, x, y + 30)

        # Center dot
        dot_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 255))
        dot_pen.setWidth(1)
        painter.setPen(dot_pen)
        painter.setBrush(QBrush(accent))
        painter.drawEllipse(x - 4, y - 4, 8, 8)

    def _draw_label(self, painter: QPainter) -> None:
        """Draw the action description label near the highlight."""
        if not self._highlight_rect or not self._label_text:
            return

        rect = self._highlight_rect

        # Position the label below the highlight
        label_x = rect.left()
        label_y = rect.bottom() + 12

        # Background pill
        font = QFont(Fonts.BODY, FontSizes.SM)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self._label_text)
        text_height = metrics.height()

        pill_rect = QRect(
            label_x - 8, label_y - 2,
            text_width + 16, text_height + 8,
        )

        # Dark pill background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(12, 14, 20, 220)))
        painter.drawRoundedRect(pill_rect, 6, 6)

        # Accent border
        accent = QColor(Colors.ACCENT)
        pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 160))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(pill_rect, 6, 6)

        # Text
        painter.setPen(QColor(Colors.TEXT_PRIMARY))
        painter.drawText(label_x, label_y + text_height - 2, self._label_text)

    # ── Animation ──────────────────────────────────────────────────────

    def _pulse_tick(self) -> None:
        """Animate the pulse alpha for the glowing effect."""
        step = 6
        if self._pulse_increasing:
            self._pulse_alpha += step
            if self._pulse_alpha >= 220:
                self._pulse_alpha = 220
                self._pulse_increasing = False
        else:
            self._pulse_alpha -= step
            if self._pulse_alpha <= 80:
                self._pulse_alpha = 80
                self._pulse_increasing = True

        self.update()

"""
Design System Tokens — colors, fonts, spacing, gradients, animations.

DEV 3 owns this module.

All UI components import their styling from here.
No hardcoded colors or font sizes anywhere else.
"""

from __future__ import annotations


# ── Colors ─────────────────────────────────────────────────────────────

class Colors:
    """Odus color palette — Obsidian Design System."""

    BG_PRIMARY = "#0c0e14"           # Deep dark background (Obsidian)
    BG_SECONDARY = "#11131a"         # Card / panel backgrounds
    BG_ELEVATED = "#171921"          # Elevated surfaces
    BG_GLASS = "rgba(12, 14, 20, 0.3)" # Glass background with obsidian tint
    BG_SIDEBAR = "#0f1118"           # Sidebar gradient start

    ACCENT = "#ba9eff"               # Vibrant Purple
    ACCENT_HOVER = "#c5aeff"
    ACCENT_MUTED = "#8455ef"
    ACCENT_GLOW = "rgba(186, 158, 255, 0.25)"

    SUCCESS = "#22c55e"              # Green
    SUCCESS_GLOW = "rgba(34, 197, 94, 0.2)"
    WARNING = "#f59e0b"              # Amber (clean warning, not pink)
    WARNING_GLOW = "rgba(245, 158, 11, 0.2)"
    DANGER = "#ff6e84"               # Bright Error / Danger
    DANGER_GLOW = "rgba(255, 110, 132, 0.2)"

    TEXT_PRIMARY = "#e5e4ed"         # Light text (Obsidian contrast)
    TEXT_SECONDARY = "#8b8b96"       # Muted text
    TEXT_ACCENT = "#ba9eff"          # Accent-tinted text
    TEXT_DIM = "#555566"             # Very muted text (timestamps etc.)

    BORDER = "rgba(116, 117, 125, 0.15)"  # Ghost Border
    BORDER_ACTIVE = "rgba(186, 158, 255, 0.4)"
    BORDER_SUBTLE = "rgba(255, 255, 255, 0.06)"

    # Terminal-specific
    TERMINAL_BG = "#0a0c10"
    TERMINAL_TEXT = "#e5e4ed"
    TERMINAL_GREEN = "#22c55e"
    TERMINAL_RED = "#ff6e84"
    TERMINAL_YELLOW = "#f59e0b"
    TERMINAL_BLUE = "#60a5fa"
    TERMINAL_MAGENTA = "#c084fc"
    TERMINAL_CYAN = "#22d3ee"
    TERMINAL_WHITE = "#e5e4ed"
    TERMINAL_DIM = "#555566"

    # Permission card states
    PERMISSION_PENDING = "#f59e0b"    # Amber
    PERMISSION_ALLOWED = "#22c55e"    # Green
    PERMISSION_DENIED = "#ff6e84"     # Red


# ── Typography ─────────────────────────────────────────────────────────

class Fonts:
    """Font families used across the UI."""

    HEADING = "Inter"
    BODY = "Inter"
    MONO = "JetBrains Mono"    # Ghost Terminal + code blocks


class FontSizes:
    """Font size scale (in pixels)."""

    XS = 11
    SM = 13
    MD = 15       # Body text default
    LG = 18       # Section headers
    XL = 22       # Page titles
    XXL = 28      # Hero / mascot greeting


# ── Spacing ────────────────────────────────────────────────────────────

class Spacing:
    """Spacing scale (in pixels)."""

    XS = 4
    SM = 8
    MD = 16
    LG = 24
    XL = 32
    XXL = 48


# ── Border Radius ──────────────────────────────────────────────────────

class Radii:
    """Border radius presets."""

    XS = 4
    SM = 6
    MD = 10
    LG = 16
    XL = 20
    PILL = 999     # Fully rounded
    WINDOW = 16    # Main window radius


# ── Shadows ────────────────────────────────────────────────────────────

class Shadows:
    """Shadow presets."""

    SUBTLE = "0 1px 3px rgba(0,0,0,0.3)"
    MEDIUM = "0 4px 12px rgba(0,0,0,0.4)"
    ELEVATED = "0 8px 24px rgba(0,0,0,0.5)"
    GLOW_ACCENT = "0 0 20px rgba(186, 158, 255, 0.3)"


# ── Gradients ──────────────────────────────────────────────────────────

class Gradients:
    """Gradient presets for glass/sidebar effects."""

    # Sidebar: subtle vertical gradient
    SIDEBAR = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f1118, stop:1 #11131a)"

    # Header bar: glass-like
    HEADER = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(17,19,26,0.92), stop:1 rgba(12,14,20,0.88))"

    # Accent glow (for mascot ring, buttons)
    ACCENT_RING = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ba9eff, stop:1 #8455ef)"

    # Permission card backgrounds
    PERMISSION_PENDING_BG = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(245,158,11,0.08), stop:1 rgba(12,14,20,0.02))"
    PERMISSION_ALLOWED_BG = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(34,197,94,0.08), stop:1 rgba(12,14,20,0.02))"
    PERMISSION_DENIED_BG = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255,110,132,0.08), stop:1 rgba(12,14,20,0.02))"

    # Glass panel
    GLASS = "rgba(17, 19, 26, 0.75)"


# ── Animation Presets ──────────────────────────────────────────────────

class Animations:
    """Standardized animation durations (milliseconds)."""

    INSTANT = 100
    FAST = 150
    NORMAL = 250
    SLOW = 400
    PULSE = 1200      # Mascot thinking pulse
    BOUNCE = 400       # Mascot success bounce

    # Easing curve names (for QEasingCurve)
    EASE_OUT = "OutCubic"
    EASE_IN_OUT = "InOutCubic"
    EASE_OUT_BACK = "OutBack"    # Slight overshoot (for bounce)
    EASE_LINEAR = "Linear"


# ── Glass Style Helper ─────────────────────────────────────────────────

class GlassStyle:
    """
    Helper for generating glassmorphism-style QSS strings.

    Qt doesn't support backdrop-filter natively, so we simulate
    glass using semi-transparent backgrounds + ghost borders.
    """

    @staticmethod
    def panel(bg_alpha: float = 0.75, border: bool = True, radius: int = Radii.LG) -> str:
        """Glass panel style string."""
        r, g, b = 17, 19, 26
        alpha = int(bg_alpha * 255)
        style = f"background-color: rgba({r}, {g}, {b}, {alpha});"
        style += f" border-radius: {radius}px;"
        if border:
            style += f" border: 1px solid {Colors.BORDER_SUBTLE};"
        return style

    @staticmethod
    def card(accent_color: str = Colors.ACCENT, radius: int = Radii.MD) -> str:
        """Glass card with accent left border."""
        return (
            f"background-color: {Colors.BG_ELEVATED};"
            f" border-radius: {radius}px;"
            f" border-left: 3px solid {accent_color};"
            f" border: 1px solid {Colors.BORDER_SUBTLE};"
        )


# ── Layout ─────────────────────────────────────────────────────────────

class Layout:
    """Layout constants for the unified window."""

    # Unified window
    WINDOW_MIN_WIDTH = 400
    WINDOW_MIN_HEIGHT = 400
    WINDOW_DEFAULT_WIDTH = 900
    WINDOW_DEFAULT_HEIGHT = 650

    # Sidebar
    SIDEBAR_WIDTH = 180

    # Header
    HEADER_HEIGHT = 44

    # Mascot in sidebar
    MASCOT_SIZE = 100

    # Input bar
    INPUT_HEIGHT = 50

    # Safety tier badge colors
    TIER_COLORS = {
        1: Colors.SUCCESS,
        2: Colors.WARNING,
        3: Colors.DANGER,
    }

    TIER_LABELS = {
        1: "SAFE",
        2: "CAUTION",
        3: "DANGER",
    }

"""
Design System Tokens — colors, fonts, spacing.

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

    ACCENT = "#ba9eff"               # Vibrant Purple
    ACCENT_HOVER = "#c5aeff"
    ACCENT_MUTED = "#8455ef"

    SUCCESS = "#22c55e"              # Green
    WARNING = "#ffb2b9"              # Softened warning / secondary error
    DANGER = "#ff6e84"               # Bright Error / Danger

    TEXT_PRIMARY = "#e5e4ed"         # Light text (Obsidian contrast)
    TEXT_SECONDARY = "#aaaab3"       # Muted text
    TEXT_ACCENT = "#ba9eff"          # Accent-tinted text

    BORDER = "rgba(116, 117, 125, 0.2)" # Ghost Border
    BORDER_ACTIVE = "rgba(186, 158, 255, 0.4)"

    # Terminal-specific
    TERMINAL_BG = "#0c0e14"
    TERMINAL_TEXT = "#e5e4ed"
    TERMINAL_GREEN = "#22c55e"
    TERMINAL_RED = "#ff6e84"
    TERMINAL_YELLOW = "#f67ca3"
    TERMINAL_BLUE = "#ba9eff"


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

    SM = 6
    MD = 10
    LG = 16
    PILL = 999     # Fully rounded


# ── Shadows ────────────────────────────────────────────────────────────

class Shadows:
    """Box shadow presets (CSS-style strings for Flet Container)."""

    SUBTLE = "0 1px 3px rgba(0,0,0,0.3)"
    MEDIUM = "0 4px 12px rgba(0,0,0,0.4)"
    ELEVATED = "0 8px 24px rgba(0,0,0,0.5)"


class Layout:
    """Layout constants for the floating mascot + modal UI."""

    # Normal small window (mascot only)
    MASCOT_WIDTH = 120
    MASCOT_HEIGHT = 160

    # Expanded Modal (terminal)
    MODAL_WIDTH = 800
    MODAL_HEIGHT = 600

    # Window sizes (when frameless and transparent, Flet window still needs enough space for the expanded modal)
    WINDOW_MIN_WIDTH = MODAL_WIDTH + MASCOT_WIDTH + 100
    WINDOW_MIN_HEIGHT = MODAL_HEIGHT + MASCOT_HEIGHT + 100

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

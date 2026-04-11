"""
Design System Tokens — colors, fonts, spacing.

DEV 3 owns this module.

All UI components import their styling from here.
No hardcoded colors or font sizes anywhere else.
"""

from __future__ import annotations


# ── Colors ─────────────────────────────────────────────────────────────

class Colors:
    """Odus color palette — dark mode first."""

    BG_PRIMARY = "#0f1117"           # Deep dark background
    BG_SECONDARY = "#1a1d27"         # Card / panel backgrounds
    BG_ELEVATED = "#22252f"          # Elevated surfaces (dialogs, tooltips)
    BG_GLASS = "rgba(255,255,255,0.05)"

    ACCENT = "#6c63ff"               # Primary purple
    ACCENT_HOVER = "#7b73ff"
    ACCENT_MUTED = "#4a4494"

    SUCCESS = "#22c55e"              # Green — safe / success / tier 1
    WARNING = "#eab308"              # Yellow — caution / tier 2
    DANGER = "#ef4444"               # Red — danger / tier 3 / error

    TEXT_PRIMARY = "#e4e4e7"         # Light text on dark bg
    TEXT_SECONDARY = "#a1a1aa"       # Muted text
    TEXT_ACCENT = "#c4c0ff"          # Accent-tinted text

    BORDER = "rgba(255,255,255,0.08)"
    BORDER_ACTIVE = "rgba(108,99,255,0.4)"

    # Terminal-specific
    TERMINAL_BG = "#0a0c10"
    TERMINAL_TEXT = "#c9d1d9"
    TERMINAL_GREEN = "#3fb950"
    TERMINAL_RED = "#f85149"
    TERMINAL_YELLOW = "#d29922"
    TERMINAL_BLUE = "#58a6ff"


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


# ── Layout ─────────────────────────────────────────────────────────────

class Layout:
    """Layout constants for the landscape UI."""

    WINDOW_MIN_WIDTH = 900
    WINDOW_MIN_HEIGHT = 520
    WINDOW_DEFAULT_WIDTH = 1100
    WINDOW_DEFAULT_HEIGHT = 620

    SIDEBAR_WIDTH = 260            # Mascot + status panel
    TERMINAL_MIN_HEIGHT = 200

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

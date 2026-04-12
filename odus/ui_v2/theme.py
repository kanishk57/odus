"""
Design System Tokens — Editorial Obsidian (v2).
Derived from Stitch Design System Specification.
"""

from __future__ import annotations


# ── Colors ─────────────────────────────────────────────────────────────

class Colors:
    """Editorial Obsidian color palette."""

    # Surfaces (Shadow Console Philosophy)
    BG_BASE = "#0c0e14"              # Deep dark base
    BG_LEVEL_1 = "#11131a"           # Secondary navigation / grouping
    BG_LEVEL_2 = "#171921"           # Active chat bubbles / primary input
    BG_LEVEL_3 = "#23262e"           # Hover states / high-priority overlays
    BG_LOWEST = "#000000"            # Code blocks

    # Brand
    PRIMARY = "#ba9eff"              # Ethereal Purple
    PRIMARY_CONTAINER = "#ac91f1"    # For gradients
    ACCENT = "#ba9eff"               # Alias for PRIMARY

    # Functional
    SUCCESS = "#22c55e"              # Green
    WARNING = "#f59e0b"              # Amber
    ERROR = "#ff6e84"                # Red
    DANGER = "#ff6e84"

    # Text (Reduced eye strain)
    TEXT_PRIMARY = "#e7e7f0"         # On surface
    TEXT_SECONDARY = "#aaaab3"       # On surface variant
    TEXT_ACCENT = "#ba9eff"

    # Borders (Ghost Borders - 15% opacity)
    BORDER_GHOST = "rgba(70, 72, 79, 0.15)"
    BORDER_SUBTLE = "rgba(231, 231, 240, 0.06)"


# ── Typography ─────────────────────────────────────────────────────────

class Fonts:
    """Font families for Editorial Obsidian."""

    HEADLINE = "Space Grotesk"       # Hacker-luxury vibe
    BODY = "Inter"                   # Optimized for scanning
    MONO = "JetBrains Mono"


class FontSizes:
    """Font size scale (in pixels)."""

    XS = 11
    LABEL_SM = 11                    # Metadata / timestamps
    SM = 13
    MD = 14                          # Default body text
    LG = 18                          # Section headers
    XL = 24                          # Display / Page titles


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
    """Sharp, technical radii presets."""

    SM = 2
    MD = 6                           # Default for bubbles/cards
    LG = 12
    FULL = 999                       # Circles


# ── Gradients ──────────────────────────────────────────────────────────

class Gradients:
    """Signature texture gradients."""

    # Primary action texture
    PRIMARY_TEXTURE = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ba9eff, stop:1 #ac91f1)"

    # Glass backdrop
    GLASS_BACKDROP = "rgba(41, 44, 53, 0.6)"  # surface_bright @ 60%


# ── Layout ─────────────────────────────────────────────────────────────

class Layout:
    """Sidebar and Window layout specifications."""

    SIDEBAR_WIDTH_EXPANDED = 450     # More substantial professional width
    SIDEBAR_WIDTH_COLLAPSED = 20     # Slightly wider dock strip for visibility

    # Window Fallback
    WINDOW_INITIAL_WIDTH = 960
    WINDOW_INITIAL_HEIGHT = 540      # 16:9 Aspect Ratio

    # The Node (Floating Trigger / Dock Handle)
    NODE_SIZE = 48

    # Padding
    CONTENT_PADDING = 24
    BUBBLE_GUTTER = 12

    # Animation
    TRANSITION_SPEED = 300           # ms

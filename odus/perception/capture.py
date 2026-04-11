"""
Screen Capture Engine — Dual-backend (X11 + Wayland).

DEV 1 owns this module.

Strategy:
  1. Detect session type via $XDG_SESSION_TYPE
  2. X11/XWayland → use `mss` (fast, low-level)
  3. Wayland → fallback to `grim` via subprocess (wlroots)
     → or `gnome-screenshot` (GNOME Wayland)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass

import mss
import mss.tools
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class CaptureResult:
    """Raw capture output."""

    png_bytes: bytes
    width: int
    height: int


class ScreenCapture:
    """
    Captures the full screen or a region, with automatic backend selection.

    Usage:
        cap = ScreenCapture()
        result = await cap.grab_full_screen()
        compressed = cap.compress(result.png_bytes)
    """

    def __init__(self) -> None:
        self._session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self._backend = self._select_backend()
        logger.info(
            "ScreenCapture initialized | session=%s | backend=%s",
            self._session_type,
            self._backend.__name__,
        )

    def _select_backend(self):
        """Pick the best capture backend for the current session."""
        if self._session_type != "wayland":
            return self._capture_x11

        # Wayland: try grim first (wlroots), then gnome-screenshot
        if shutil.which("grim"):
            logger.info("Wayland detected — using grim backend")
            return self._capture_grim
        elif shutil.which("gnome-screenshot"):
            logger.info("Wayland detected — using gnome-screenshot backend")
            return self._capture_gnome
        else:
            logger.warning(
                "Wayland detected but no compatible tool found. "
                "Falling back to mss (may fail)."
            )
            return self._capture_x11

    # ── Public API ──────────────────────────────────────────────────────

    async def grab_full_screen(self) -> CaptureResult:
        """Capture the entire primary screen. Returns PNG bytes."""
        return await self._backend()

    async def grab_region(self, x: int, y: int, w: int, h: int) -> CaptureResult:
        """Capture a specific region. Falls back to full + crop."""
        full = await self._backend()
        img = Image.open(io.BytesIO(full.png_bytes))
        cropped = img.crop((x, y, x + w, y + h))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        return CaptureResult(
            png_bytes=buf.getvalue(),
            width=w,
            height=h,
        )

    @staticmethod
    def compress(
        png_bytes: bytes,
        max_width: int = 1280,
        jpeg_quality: int = 75,
    ) -> bytes:
        """
        Compress a PNG screenshot for the Vision API.

        - Resizes to max_width (preserving aspect ratio)
        - Converts to JPEG at the given quality
        - Typical output: 150–300 KB (well under Gemini's 7 MB inline limit)
        """
        img = Image.open(io.BytesIO(png_bytes))
        ratio = max_width / img.width
        if ratio < 1:
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
        compressed = buf.getvalue()

        logger.debug(
            "Compressed: %d bytes → %d bytes (%.0f%% reduction)",
            len(png_bytes),
            len(compressed),
            (1 - len(compressed) / len(png_bytes)) * 100,
        )
        return compressed

    # ── Backends (private) ──────────────────────────────────────────────

    async def _capture_x11(self) -> CaptureResult:
        """Capture via mss (X11 / XWayland)."""
        # Note: mss is synchronous, but we run it in a thread to keep the loop free
        return await asyncio.to_thread(self._grab_mss)

    def _grab_mss(self) -> CaptureResult:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            png_bytes = mss.tools.to_png(shot.rgb, shot.size)
            return CaptureResult(
                png_bytes=png_bytes,
                width=shot.width,
                height=shot.height,
            )

    async def _capture_grim(self) -> CaptureResult:
        """Capture via grim (Wayland / wlroots compositors)."""
        proc = await asyncio.create_subprocess_exec(
            "grim", "-t", "png", "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"grim failed: {stderr.decode()}")
            
        img = Image.open(io.BytesIO(stdout))
        return CaptureResult(
            png_bytes=stdout,
            width=img.width,
            height=img.height,
        )

    async def _capture_gnome(self) -> CaptureResult:
        """Capture via gnome-screenshot (GNOME Wayland)."""
        import uuid

        tmp_name = f"/tmp/odus-screenshot-{uuid.uuid4().hex}.png"
        try:
            proc = await asyncio.create_subprocess_exec(
                "gnome-screenshot", "-f", tmp_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"gnome-screenshot failed: {stderr.decode()}")

            if not os.path.exists(tmp_name):
                raise RuntimeError("gnome-screenshot did not produce a file")
                
            # Reading is IO-bound, run in thread
            png_bytes = await asyncio.to_thread(self._read_file, tmp_name)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

        if not png_bytes:
            raise RuntimeError("gnome-screenshot produced an empty file")

        img = Image.open(io.BytesIO(png_bytes))
        return CaptureResult(
            png_bytes=png_bytes,
            width=img.width,
            height=img.height,
        )

    @staticmethod
    def _read_file(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

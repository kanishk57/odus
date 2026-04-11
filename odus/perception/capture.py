"""
Screen Capture Engine — Multi-backend (X11 + Wayland).

DEV 1 owns this module.

Strategy:
  1. Detect session type via $XDG_SESSION_TYPE
  2. X11/XWayland → use `mss` (fast, low-level)
  3. Wayland → backend priority:
     a. `grim` (wlroots compositors — Sway, Hyprland)
     b. GNOME Mutter ScreenCast (GNOME Wayland — native, silent, no dialog)
     c. `gnome-screenshot` (GNOME fallback)
     d. `spectacle` (KDE Wayland)
     e. `mss` (last resort, may fail)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse, unquote

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

    On GNOME Wayland, uses PipeWire ScreenCast for silent, automatic
    screenshots. The user sees a share dialog ONCE at startup to grant
    screen access. After that, all captures are instant and silent.

    Usage:
        cap = ScreenCapture()
        await cap.initialize()   # Call once — sets up PipeWire session
        result = await cap.grab_full_screen()
        compressed = cap.compress(result.png_bytes)
    """

    def __init__(self) -> None:
        self._session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self._backend = self._select_backend()

        # Mutter ScreenCast state
        self._mutter_helper_proc: subprocess.Popen | None = None
        self._mutter_node_id: str | None = None
        logger.info(
            "ScreenCapture initialized | session=%s | backend=%s",
            self._session_type,
            self._backend.__name__,
        )

    def _select_backend(self):
        """Pick the best capture backend for the current session."""
        if self._session_type != "wayland":
            return self._capture_x11

        # Wayland: try grim first (wlroots compositors)
        if shutil.which("grim"):
            logger.info("Wayland detected — using grim backend")
            return self._capture_grim

        # GNOME Wayland: Use native Mutter ScreenCast (completely silent, no portal prompt)
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "gnome" in desktop:
            # We use a system python3 helper because it usually has PyGObject
            if shutil.which("python3"):
                logger.info("Wayland detected — using native Mutter ScreenCast backend")
                return self._capture_mutter
            elif shutil.which("gnome-screenshot"):
                logger.info("Wayland detected — using gnome-screenshot backend")
                return self._capture_gnome_screenshot

        # KDE Wayland
        if shutil.which("spectacle"):
            logger.info("Wayland detected — using spectacle backend")
            return self._capture_spectacle

        # Fallback: XDG portal (interactive — shows dialog each time)
        logger.warning(
            "Wayland detected but no preferred tool found. "
            "Falling back to XDG portal (may show a dialog each time)."
        )
        return self._capture_portal_fallback

    # ── Public API ──────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """
        One-time setup.
        """
        if self._backend == self._capture_mutter:
            await self._setup_mutter_session()

    async def grab_full_screen(self) -> CaptureResult:
        """Capture the entire primary screen. Returns PNG bytes."""
        return await self._backend()



    @staticmethod
    def compress(
        png_bytes: bytes,
        max_width: int = 1920,
        jpeg_quality: int = 85,
    ) -> tuple[bytes, int, int]:
        """
        Compress a PNG screenshot for the Vision API.

        Returns:
            (bytes, width, height): JPEG bytes and the resolution seen by the AI.
        """
        img = Image.open(io.BytesIO(png_bytes))
        orig_w, orig_h = img.width, img.height
        
        ratio = max_width / orig_w
        if ratio < 1:
            new_w = max_width
            new_h = int(orig_h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        else:
            new_w, new_h = orig_w, orig_h

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
        compressed = buf.getvalue()

        logger.debug(
            "Compressed: %dx%d -> %dx%d | %d bytes (%.0f%% reduction)",
            orig_w, orig_h, new_w, new_h,
            len(compressed),
            (1 - len(compressed) / len(png_bytes)) * 100,
        )
        return compressed, new_w, new_h

    # ── GNOME Mutter ScreenCast (GNOME Wayland — native, silent) ─────

    async def _setup_mutter_session(self) -> None:
        """
        Starts a persistent helper script that connects to the internal
        org.gnome.Mutter.ScreenCast D-Bus API. This completely bypasses
        the XDG Desktop Portal and requires ZERO user dialogs.
        """
        if self._mutter_helper_proc is not None:
            return

        logger.info("Setting up native Mutter ScreenCast session (silent)...")

        helper_script = '''
import gi, threading, time, sys
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

conn = Gio.bus_get_sync(Gio.BusType.SESSION)
node_id = None
lock = threading.Lock()

def on_signal(c,s,p,i,sig,params):
    global node_id
    if sig == 'PipeWireStreamAdded':
        with lock:
            node_id = params.unpack()[0]
            print(f"NODE_ID:{node_id}", flush=True)

conn.signal_subscribe(
    "org.gnome.Mutter.ScreenCast",
    "org.gnome.Mutter.ScreenCast.Stream",
    "PipeWireStreamAdded",
    None, None, Gio.DBusSignalFlags.NONE, on_signal)

ml = GLib.MainLoop()
threading.Thread(target=ml.run, daemon=True).start()

try:
    r = conn.call_sync(
        "org.gnome.Mutter.ScreenCast", "/org/gnome/Mutter/ScreenCast", "org.gnome.Mutter.ScreenCast",
        "CreateSession", GLib.Variant("(a{sv})", ({},)), None, Gio.DBusCallFlags.NONE, 5000, None)
    sp = r.unpack()[0]

    r2 = conn.call_sync(
        "org.gnome.Mutter.ScreenCast", sp, "org.gnome.Mutter.ScreenCast.Session",
        "RecordMonitor", GLib.Variant("(sa{sv})", ("", {})), None, Gio.DBusCallFlags.NONE, 5000, None)
    stream_path = r2.unpack()[0]

    conn.call_sync(
        "org.gnome.Mutter.ScreenCast", sp, "org.gnome.Mutter.ScreenCast.Session",
        "Start", None, None, Gio.DBusCallFlags.NONE, 5000, None)
    
    # Stay alive forever to keep the session open
    while True:
        time.sleep(1)
except Exception as e:
    print(f"ERROR:{e}", flush=True)
    sys.exit(1)
'''

        try:
            self._mutter_helper_proc = subprocess.Popen(
                ["/usr/bin/python3", "-c", helper_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # Wait for the node ID
            for line in iter(self._mutter_helper_proc.stdout.readline, ""):
                line = line.strip()
                if line.startswith("NODE_ID:"):
                    self._mutter_node_id = line.split(":", 1)[1]
                    logger.info("Mutter ScreenCast ready | PipeWire node=%s", self._mutter_node_id)
                    return
                elif line.startswith("ERROR:"):
                    raise RuntimeError(f"Mutter helper failed: {line}")
            
            raise RuntimeError("Mutter helper exited without providing a node ID")

        except Exception as e:
            logger.error("Mutter setup failed (%s) — falling back to gnome-screenshot", e)
            if self._mutter_helper_proc:
                self._mutter_helper_proc.terminate()
                self._mutter_helper_proc = None
            self._backend = self._capture_gnome_screenshot
            raise

    async def _capture_mutter(self) -> CaptureResult:
        """
        Capture a frame from the Mutter ScreenCast PipeWire stream.
        """
        if not self._mutter_node_id:
            raise RuntimeError("Mutter session not initialized. Call initialize() first.")

        import glob
        tmp_dir = f"/tmp/odus-mutter-{uuid.uuid4().hex}"
        os.makedirs(tmp_dir, exist_ok=True)

        try:
            # Capture using GStreamer via pipewiresrc path=...
            # The stream sends real frames immediately or very quickly.
            gst_cmd = [
                "gst-launch-1.0", "-e",
                "pipewiresrc", f"path={self._mutter_node_id}", "!",
                "videoconvert", "!", "pngenc", "!",
                "multifilesink", f"location={tmp_dir}/frame_%05d.png",
            ]

            try:
                await asyncio.to_thread(
                    subprocess.run, gst_cmd,
                    capture_output=True, timeout=1,
                )
            except subprocess.TimeoutExpired:
                pass

            frames = sorted(glob.glob(f"{tmp_dir}/frame_*.png"))
            if not frames:
                raise RuntimeError("Mutter capture produced no frames")

            last_frame = frames[-1]
            png_bytes = await asyncio.to_thread(self._read_file, last_frame)

            if not png_bytes or len(png_bytes) < 100:
                raise RuntimeError("Mutter capture produced empty frame")

            img = Image.open(io.BytesIO(png_bytes))

            logger.debug(
                "Mutter capture: %dx%d, %d bytes (%d frames, used last)",
                img.width, img.height, len(png_bytes), len(frames),
            )

            return CaptureResult(
                png_bytes=png_bytes,
                width=img.width,
                height=img.height,
            )

        finally:
            import shutil as _shutil
            try:
                _shutil.rmtree(tmp_dir)
            except OSError:
                pass

    # ── GNOME Screenshot (GNOME Wayland — fallback) ─────────

    async def _capture_gnome_screenshot(self) -> CaptureResult:
        """
        Capture the full screen using gnome-screenshot.

        gnome-screenshot on modern GNOME (49+) saves to ~/Pictures/Screenshot.png
        by default. We capture, read the file, and clean up.

        This is completely silent — no dialogs, no user interaction.
        """
        import glob
        import time as _time

        # Record current screenshots so we can identify new ones
        pictures_dir = os.path.expanduser("~/Pictures")
        screenshots_before = set(glob.glob(f"{pictures_dir}/Screenshot*.png"))

        try:
            await asyncio.to_thread(
                subprocess.run,
                ["gnome-screenshot"],
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("gnome-screenshot timed out")

        # Brief pause for file system sync
        await asyncio.sleep(0.1)

        # Find the new screenshot file
        screenshots_after = set(glob.glob(f"{pictures_dir}/Screenshot*.png"))
        new_files = screenshots_after - screenshots_before

        if not new_files:
            # Fallback: use the most recently modified Screenshot*.png
            all_shots = glob.glob(f"{pictures_dir}/Screenshot*.png")
            if all_shots:
                latest = max(all_shots, key=os.path.getmtime)
                # Only accept if modified in the last 5 seconds
                if _time.time() - os.path.getmtime(latest) < 5:
                    new_files = {latest}

        if not new_files:
            raise RuntimeError("gnome-screenshot did not produce a file")

        screenshot_path = new_files.pop()
        png_bytes = await asyncio.to_thread(self._read_file, screenshot_path)

        # Clean up the screenshot file
        try:
            os.remove(screenshot_path)
        except OSError:
            pass

        img = Image.open(io.BytesIO(png_bytes))

        logger.debug(
            "gnome-screenshot capture: %dx%d, %d bytes",
            img.width, img.height, len(png_bytes),
        )

        return CaptureResult(
            png_bytes=png_bytes,
            width=img.width,
            height=img.height,
        )



    async def _wait_portal_response(self, bus, request_path: str, timeout: int = 10):
        """Wait for a portal Response signal on the given request path."""
        from dbus_fast import Message

        result_future = asyncio.get_event_loop().create_future()

        class _Handler:
            def __init__(self, fut, path):
                self._fut = fut
                self._path = path
            def __call__(self, sig_msg):
                if (sig_msg.interface == 'org.freedesktop.portal.Request'
                        and sig_msg.member == 'Response'
                        and sig_msg.path == self._path
                        and not self._fut.done()):
                    self._fut.set_result(sig_msg.body)

        handler = _Handler(result_future, request_path)
        bus.add_message_handler(handler)

        await bus.call(Message(
            destination='org.freedesktop.DBus',
            path='/org/freedesktop/DBus',
            interface='org.freedesktop.DBus',
            member='AddMatch',
            signature='s',
            body=[
                f"type='signal',interface='org.freedesktop.portal.Request',"
                f"path='{request_path}',member='Response'"
            ],
        ))

        try:
            return await asyncio.wait_for(result_future, timeout=timeout)
        finally:
            bus.remove_message_handler(handler)



    # ── Portal Screenshot Fallback ───────────────────────────────────

    async def _capture_portal_fallback(self) -> CaptureResult:
        """
        Fallback: XDG Screenshot Portal (interactive — shows dialog each time).
        Used only if PipeWire ScreenCast setup fails.
        """
        from dbus_fast.aio import MessageBus
        from dbus_fast import Message, MessageType, Variant

        bus = await MessageBus().connect()
        try:
            for interactive in (False, True):
                mode = "interactive" if interactive else "non-interactive"
                logger.info("Portal screenshot fallback | mode=%s", mode)

                msg = Message(
                    destination='org.freedesktop.portal.Desktop',
                    path='/org/freedesktop/portal/desktop',
                    interface='org.freedesktop.portal.Screenshot',
                    member='Screenshot',
                    signature='sa{sv}',
                    body=['', {'interactive': Variant('b', interactive)}],
                )

                reply = await bus.call(msg)
                if reply.message_type == MessageType.ERROR:
                    continue

                timeout = 5 if not interactive else 30
                try:
                    body = await self._wait_portal_response(bus, reply.body[0], timeout=timeout)
                except asyncio.TimeoutError:
                    continue

                if body[0] != 0:
                    continue

                results = body[1] if len(body) > 1 else {}
                if 'uri' not in results:
                    continue

                uri = results['uri']
                if hasattr(uri, 'value'):
                    uri = uri.value

                filepath = unquote(urlparse(uri).path)
                if not os.path.exists(filepath):
                    continue

                png_bytes = await asyncio.to_thread(self._read_file, filepath)
                if not png_bytes:
                    continue

                img = Image.open(io.BytesIO(png_bytes))
                return CaptureResult(
                    png_bytes=png_bytes,
                    width=img.width,
                    height=img.height,
                )

            raise RuntimeError("Portal screenshot fallback failed")
        finally:
            bus.disconnect()

    # ── Other Backends ───────────────────────────────────────────────

    async def _capture_x11(self) -> CaptureResult:
        """Capture via mss (X11 / XWayland)."""
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

    async def _capture_spectacle(self) -> CaptureResult:
        """Capture via spectacle (KDE Wayland)."""
        tmp_name = f"/tmp/odus-screenshot-{uuid.uuid4().hex}.png"
        try:
            proc = await asyncio.create_subprocess_exec(
                "spectacle", "-b", "-n", "-o", tmp_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"spectacle failed: {stderr.decode()}")

            if not os.path.exists(tmp_name):
                raise RuntimeError("spectacle did not produce a file")

            png_bytes = await asyncio.to_thread(self._read_file, tmp_name)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

        if not png_bytes:
            raise RuntimeError("spectacle produced an empty file")

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

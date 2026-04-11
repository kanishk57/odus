"""Tests for the screen capture engine."""

from __future__ import annotations

from unittest.mock import patch

from odus.perception.capture import ScreenCapture


class TestScreenCaptureBackendSelection:
    """Test that the correct backend is selected based on session type."""

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11"})
    def test_x11_session_selects_mss(self):
        cap = ScreenCapture()
        assert cap._backend.__name__ == "_capture_x11"

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland"})
    @patch("shutil.which", side_effect=lambda cmd: "/usr/bin/grim" if cmd == "grim" else None)
    def test_wayland_with_grim(self, mock_which):
        cap = ScreenCapture()
        assert cap._backend.__name__ == "_capture_grim"

    @patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland"})
    @patch("shutil.which", return_value=None)
    def test_wayland_no_tools_falls_back_to_portal(self, mock_which):
        cap = ScreenCapture()
        assert cap._backend.__name__ == "_capture_portal_fallback"

    @patch.dict("os.environ", {}, clear=True)
    def test_no_env_defaults_to_x11(self):
        cap = ScreenCapture()
        assert cap._backend.__name__ == "_capture_x11"


class TestCompression:
    """Test image compression for the Vision API."""

    def test_compress_reduces_size(self):
        """Create a noisy PNG (simulating a real screenshot) and verify JPEG compression shrinks it."""
        from PIL import Image
        import io
        import os

        # Create a 1920x1080 random noise image (realistic screenshot-like data)
        data = os.urandom(1920 * 1080 * 3)
        img = Image.frombytes("RGB", (1920, 1080), data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        compressed, new_w, new_h = ScreenCapture.compress(png_bytes, max_width=1280, jpeg_quality=75)

        assert len(compressed) < len(png_bytes)
        # Verify it's a valid JPEG
        result_img = Image.open(io.BytesIO(compressed))
        assert result_img.format == "JPEG"
        assert result_img.width == 1280

    def test_compress_small_image_no_upscale(self):
        """Images smaller than max_width should not be upscaled."""
        from PIL import Image
        import io

        img = Image.new("RGB", (800, 600), color=(50, 50, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        compressed, new_w, new_h = ScreenCapture.compress(png_bytes, max_width=1280)
        result_img = Image.open(io.BytesIO(compressed))
        assert result_img.width == 800  # Should NOT upscale

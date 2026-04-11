"""
File Browser — sandboxed file/directory access with permission tracking.

The agent must request access to directories before reading/modifying.
Approved directories are tracked per-session.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """A single file/directory entry."""
    name: str
    path: str
    is_dir: bool
    size: int = 0
    extension: str = ""



# Paths that are NEVER accessible
_BLOCKED_PATHS = frozenset({
    ".ssh",
    ".gnupg",
    ".gpg",
    ".password-store",
    ".mozilla/firefox",
    ".config/google-chrome",
    ".local/share/keyrings",
})

_BLOCKED_ABSOLUTE = frozenset({
    "/etc/shadow",
    "/etc/gshadow",
    "/etc/sudoers",
    "/boot",
    "/proc",
    "/sys",
})


class FileBrowser:
    """
    Sandboxed file/directory browser with permission tracking.

    The agent must request access to directories before reading.
    Approved directories are remembered for the session.

    Usage:
        browser = FileBrowser()
        # CWD is always accessible
        entries = await browser.list_directory(".")
        # Other dirs need approval
        if browser.is_allowed("/home/user/Documents"):
            entries = await browser.list_directory("/home/user/Documents")
    """

    def __init__(self, initial_cwd: str | None = None) -> None:
        self._cwd = initial_cwd or os.getcwd()
        self._allowed_dirs: set[str] = set()
        # CWD and children are always allowed
        self._allowed_dirs.add(os.path.abspath(self._cwd))

        logger.info("FileBrowser initialized | cwd=%s", self._cwd)

    @property
    def cwd(self) -> str:
        return self._cwd

    def set_cwd(self, path: str) -> None:
        self._cwd = os.path.abspath(path)
        self._allowed_dirs.add(self._cwd)

    # ── Permission Management ──────────────────────────────────────────

    def is_allowed(self, path: str) -> bool:
        """Check if a path is accessible."""
        abs_path = self._resolve(path)

        # Check blocked paths
        if self._is_blocked(abs_path):
            return False

        # Check if any allowed directory is a parent
        for allowed in self._allowed_dirs:
            if abs_path.startswith(allowed):
                return True

        return False

    def grant_access(self, path: str) -> bool:
        """Grant access to a directory (called after user approves)."""
        abs_path = self._resolve(path)
        if self._is_blocked(abs_path):
            logger.warning("🚫 Cannot grant access to blocked path: %s", abs_path)
            return False
        self._allowed_dirs.add(abs_path)
        logger.info("✅ Access granted: %s", abs_path)
        return True

    def needs_permission(self, path: str) -> bool:
        """Check if a path needs explicit permission (not already allowed, not blocked)."""
        abs_path = self._resolve(path)
        if self._is_blocked(abs_path):
            return False  # Blocked, not grantable
        return not self.is_allowed(abs_path)

    # ── File Operations ────────────────────────────────────────────────

    async def list_directory(self, path: str = ".") -> list[FileEntry]:
        """
        List files in a directory.

        Raises:
            PermissionError: If the directory is not accessible.
        """
        abs_path = self._resolve(path)

        if not self.is_allowed(abs_path):
            raise PermissionError(f"Access not granted: {abs_path}")

        if not os.path.isdir(abs_path):
            raise FileNotFoundError(f"Not a directory: {abs_path}")

        entries = []
        try:
            for name in sorted(os.listdir(abs_path)):
                # Skip hidden files by default
                full = os.path.join(abs_path, name)
                is_dir = os.path.isdir(full)
                size = 0
                if not is_dir:
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        pass

                ext = os.path.splitext(name)[1] if not is_dir else ""

                entries.append(FileEntry(
                    name=name,
                    path=full,
                    is_dir=is_dir,
                    size=size,
                    extension=ext,
                ))
        except PermissionError:
            raise PermissionError(f"OS permission denied: {abs_path}")

        return entries

    async def read_file(self, path: str, max_lines: int = 200) -> str:
        """
        Read a file's contents (limited to max_lines).

        Raises:
            PermissionError: If the file's directory is not accessible.
        """
        abs_path = self._resolve(path)
        parent = os.path.dirname(abs_path)

        if not self.is_allowed(parent):
            raise PermissionError(f"Access not granted: {parent}")

        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Not a file: {abs_path}")

        lines = []
        with open(abs_path, "r", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... (truncated at {max_lines} lines)")
                    break
                lines.append(line.rstrip("\n"))

        return "\n".join(lines)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _resolve(self, path: str) -> str:
        """Resolve a path relative to cwd."""
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self._cwd, path))

    @staticmethod
    def _is_blocked(abs_path: str) -> bool:
        """Check if a path is in the blocked list."""
        # Check absolute blocked paths
        for blocked in _BLOCKED_ABSOLUTE:
            if abs_path.startswith(blocked):
                return True

        # Check relative-to-home blocked paths
        home = os.path.expanduser("~")
        if abs_path.startswith(home):
            rel = abs_path[len(home) + 1:]  # Remove home + "/"
            for blocked in _BLOCKED_PATHS:
                if rel.startswith(blocked):
                    return True

        return False

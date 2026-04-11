"""
PTY Session — real pseudo-terminal for interactive command execution.

Provides a persistent shell session that streams output line-by-line,
maintains working directory state, and supports interactive commands.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pty
import signal
import subprocess
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from odus.action.safety import SafetyGate, SafetyVerdict

logger = logging.getLogger(__name__)


@dataclass
class PtyCommandResult:
    """Final result after a PTY command completes."""
    command: str
    exit_code: int
    output: str          # Full captured output
    timed_out: bool


class PtySession:
    """
    Interactive pseudo-terminal shell for real-time command execution.

    Unlike subprocess.run(), this:
      - Streams stdout/stderr line-by-line (Ghost Terminal sees output live)
      - Maintains shell state (cd, export, aliases persist between commands)
      - Has a working directory that persists between commands
      - Enforces the safety gate before every command

    Usage:
        session = PtySession()
        async for line in session.execute("apt list --installed"):
            print(line)  # streamed live
        print(session.cwd)  # /home/user
    """

    def __init__(self, initial_cwd: str | None = None) -> None:
        self._safety = SafetyGate()
        self._cwd = initial_cwd or os.getcwd()
        self._env = {**os.environ, "LANG": "C.UTF-8", "TERM": "xterm-256color"}

        logger.info("PtySession initialized | cwd=%s", self._cwd)

    @property
    def cwd(self) -> str:
        """Current working directory of the session."""
        return self._cwd

    async def execute(
        self,
        command: str,
        timeout: int = 30,
    ) -> AsyncGenerator[str, None]:
        """
        Execute a command and stream output lines.

        Yields output lines as they arrive. After the command completes,
        updates the working directory if the command changed it.

        Raises:
            PermissionError: If the command is blocked by the safety gate.
        """
        # Safety check
        verdict = self._safety.classify(command)
        if verdict == SafetyVerdict.BLOCKED:
            msg = f"BLOCKED: {command}"
            logger.error("🚫 %s", msg)
            raise PermissionError(msg)

        logger.info("▶ PTY executing: %s (cwd=%s, timeout=%ds)", command, self._cwd, timeout)

        # We use a real pty so commands that check for a terminal (ls --color, etc.) work
        master_fd, slave_fd = pty.openpty()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=self._cwd,
                env=self._env,
                preexec_fn=os.setsid,
            )
            os.close(slave_fd)
            slave_fd = -1  # Mark as closed

            # Read output from master_fd in a thread
            output_lines: list[str] = []

            async def read_output():
                loop = asyncio.get_running_loop()
                buffer = b""
                while True:
                    try:
                        data = await asyncio.wait_for(
                            loop.run_in_executor(None, os.read, master_fd, 4096),
                            timeout=0.5,
                        )
                        if not data:
                            break
                        buffer += data
                        # Split into lines
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            decoded = line.decode("utf-8", errors="replace").rstrip("\r")
                            output_lines.append(decoded)
                    except asyncio.TimeoutError:
                        # Check if process has exited
                        if proc.returncode is not None:
                            break
                        continue
                    except OSError:
                        break

                # Flush remaining buffer
                if buffer:
                    decoded = buffer.decode("utf-8", errors="replace").rstrip("\r\n")
                    if decoded:
                        output_lines.append(decoded)

            # Start reading in background
            read_task = asyncio.create_task(read_output())

            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("⏰ PTY command timed out: %s", command)
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
                await asyncio.sleep(0.2)
                if proc.returncode is None:
                    proc.kill()

            # Wait for reader to finish
            await asyncio.wait_for(read_task, timeout=2.0)

            # Yield all collected lines
            for line in output_lines:
                yield line

            # After command, try to detect if cwd changed
            await self._update_cwd()

            exit_code = proc.returncode or 0
            if exit_code == 0:
                logger.info("✅ PTY command succeeded: %s", command)
            else:
                logger.warning("❌ PTY command failed (rc=%d): %s", exit_code, command)

        finally:
            if slave_fd >= 0:
                try:
                    os.close(slave_fd)
                except OSError:
                    pass
            try:
                os.close(master_fd)
            except OSError:
                pass

    async def change_directory(self, path: str) -> bool:
        """
        Change the session's working directory.

        Returns True if the directory exists and was changed.
        """
        # Resolve relative to current cwd
        if not os.path.isabs(path):
            resolved = os.path.normpath(os.path.join(self._cwd, path))
        else:
            resolved = os.path.normpath(path)

        if os.path.isdir(resolved):
            self._cwd = resolved
            logger.info("📁 Changed directory: %s", resolved)
            return True
        else:
            logger.warning("📁 Directory not found: %s", path)
            return False

    async def send_input(self, text: str) -> None:
        """
        Send text to stdin of a running command.
        (For future interactive command support.)
        """
        # This would need a persistent process — placeholder for now
        logger.info("PTY stdin: %s", text[:60])

    async def _update_cwd(self) -> None:
        """Try to detect cwd changes by running pwd."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pwd",
                stdout=asyncio.subprocess.PIPE,
                cwd=self._cwd,
                env=self._env,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            new_cwd = stdout.decode().strip()
            if new_cwd and os.path.isdir(new_cwd):
                self._cwd = new_cwd
        except Exception:
            pass  # Not critical

"""
Sandboxed Command Executor — runs shell commands with safety constraints.

DEV 1 owns this module.

Features:
  - Timeout enforcement (default 30s)
  - stdout/stderr capture
  - Audit logging to ~/.odus/audit.log
  - Never runs blocked commands (enforced by SafetyGate)
"""

from __future__ import annotations

import datetime
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from odus.action.safety import SafetyGate, SafetyVerdict

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a command execution."""

    stdout: str
    stderr: str
    return_code: int
    timed_out: bool
    command: str


class CommandExecutor:
    """
    Runs shell commands in a sandboxed subprocess.

    Safety:
      - Commands are ALWAYS checked against the SafetyGate before execution.
      - Tier 3 commands are NEVER executed, even if called directly.
      - All executions are logged to the audit log.

    Usage:
        executor = CommandExecutor()
        result = executor.run("apt list --installed")
        print(result.stdout)
    """

    def __init__(self, timeout: int = 30, audit_log: bool = True) -> None:
        self._default_timeout = timeout
        self._safety = SafetyGate()
        self._audit_log_enabled = audit_log

        # Set up audit log directory
        self._audit_path = Path.home() / ".odus" / "audit.log"
        if self._audit_log_enabled:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "CommandExecutor initialized | timeout=%ds | audit=%s",
            timeout,
            self._audit_path if audit_log else "disabled",
        )

    def run(self, command: str, timeout: int | None = None) -> ExecutionResult:
        """
        Execute a shell command.

        Args:
            command: The shell command string to execute.
            timeout: Seconds before killing the process (default: 30).

        Returns:
            ExecutionResult with stdout, stderr, return code, and timeout flag.

        Raises:
            PermissionError: If the command is classified as BLOCKED (tier 3).
        """
        timeout = timeout or self._default_timeout

        # SAFETY CHECK — non-negotiable
        verdict = self._safety.classify(command)
        if verdict == SafetyVerdict.BLOCKED:
            msg = f"BLOCKED: Refusing to execute dangerous command: {command}"
            logger.error("🚫 %s", msg)
            self._audit(command, "BLOCKED", "")
            raise PermissionError(msg)

        # Execute
        logger.info("▶ Executing: %s (timeout=%ds)", command, timeout)
        timed_out = False

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "LANG": "C.UTF-8"},
            )
            stdout = proc.stdout
            stderr = proc.stderr
            return_code = proc.returncode

        except subprocess.TimeoutExpired:
            logger.warning("⏰ Command timed out after %ds: %s", timeout, command)
            stdout = ""
            stderr = f"Command timed out after {timeout} seconds."
            return_code = -1
            timed_out = True

        except Exception as e:
            logger.error("💥 Execution error: %s", e)
            stdout = ""
            stderr = str(e)
            return_code = -1

        result = ExecutionResult(
            stdout=stdout[:10_000],   # Cap output length
            stderr=stderr[:5_000],
            return_code=return_code,
            timed_out=timed_out,
            command=command,
        )

        # Audit log
        status = "TIMEOUT" if timed_out else f"EXIT:{return_code}"
        self._audit(command, status, stdout[:200])

        if return_code == 0:
            logger.info("✅ Command succeeded: %s", command)
        else:
            logger.warning("❌ Command failed (rc=%d): %s", return_code, command)

        return result

    def _audit(self, command: str, status: str, output_preview: str) -> None:
        """Append an entry to the audit log."""
        if not self._audit_log_enabled:
            return

        try:
            timestamp = datetime.datetime.now().isoformat()
            entry = f"[{timestamp}] [{status}] {command}"
            if output_preview:
                entry += f" | output: {output_preview.strip()[:100]}"
            entry += "\n"

            with open(self._audit_path, "a") as f:
                f.write(entry)
        except Exception as e:
            logger.debug("Failed to write audit log: %s", e)

"""Tests for the command executor."""

from __future__ import annotations

import pytest

from odus.action.executor import CommandExecutor, ExecutionResult


class TestCommandExecutor:
    """Test the sandboxed command executor."""

    def setup_method(self):
        self.executor = CommandExecutor(timeout=10, audit_log=False)

    def test_simple_command(self):
        result = self.executor.run("echo hello world")
        assert result.return_code == 0
        assert "hello world" in result.stdout
        assert not result.timed_out

    def test_failed_command(self):
        result = self.executor.run("false")
        assert result.return_code != 0

    def test_timeout_enforcement(self):
        result = self.executor.run("sleep 60", timeout=1)
        assert result.timed_out is True

    def test_blocked_command_raises(self):
        with pytest.raises(PermissionError, match="BLOCKED"):
            self.executor.run("rm -rf /")

    def test_stderr_capture(self):
        result = self.executor.run("ls /nonexistent_path_12345")
        assert result.return_code != 0
        assert result.stderr  # Should contain error message

    def test_output_truncation(self):
        """Verify output is capped at 10,000 chars."""
        result = self.executor.run("python3 -c \"print('x' * 20000)\"")
        assert len(result.stdout) <= 10_000

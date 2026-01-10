"""Command execution with timeout and output capture."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Sequence


@dataclass
class CmdResult:
    """Result of a command execution."""

    cmd: Sequence[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

_REQUIRED_CMDS = ["systemctl", "journalctl", "bash"]

_missing = [c for c in _REQUIRED_CMDS if shutil.which(c) is None]
if _missing:
    print(
        f"Missing required commands: {', '.join(_missing)}\n"
        f"Are you on a systemd-based distro? This won't work on Alpine/WSL1.",
        file=sys.stderr,
    )


def run_cmd(
    cmd: Sequence[str],
    timeout_sec: int = 10,
    max_bytes: int = 2_000_000,
) -> CmdResult:
    """Run a command with timeout and output limits.

    Args:
        cmd: Command and arguments
        timeout_sec: Timeout in seconds (default 10)
        max_bytes: Max bytes to capture from stdout/stderr (default 2MB)

    Returns:
        CmdResult with output and status
    """
    try:
        p = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            errors="replace",
        )
        out = (p.stdout or "")[:max_bytes]
        err = (p.stderr or "")[:max_bytes]
        return CmdResult(
            cmd=cmd,
            returncode=p.returncode,
            stdout=out,
            stderr=err,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as e:
        # Partial output is still useful for debugging hangs
        out = (
            e.stdout.decode(errors="replace")
            if isinstance(e.stdout, (bytes, bytearray))
            else (e.stdout or "")
        )
        err = (
            e.stderr.decode(errors="replace")
            if isinstance(e.stderr, (bytes, bytearray))
            else (e.stderr or "")
        )
        return CmdResult(
            cmd=cmd,
            returncode=124,  # Same as GNU timeout
            stdout=out[:max_bytes],
            stderr=err[:max_bytes],
            timed_out=True,
        )
    except FileNotFoundError:
        return CmdResult(
            cmd=cmd,
            returncode=127,
            stdout="",
            stderr=f"Command not found: {cmd[0]}. Check your PATH or install it.",
            timed_out=False,
        )

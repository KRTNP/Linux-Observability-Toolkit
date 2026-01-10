"""System resource collector - the stuff you always forget to check."""

from __future__ import annotations

from pathlib import Path

from toolkit.core.runner import run_cmd
from toolkit.core.bundle import write_text


def _capture(out_dir: Path, rel: str, cmd: list, timeout: int = 8):
    """Run cmd, dump output to file."""
    r = run_cmd(cmd, timeout_sec=timeout)
    write_text(out_dir / rel, r.stdout + "\n\n" + r.stderr)


def collect_resource(out_dir: Path):
    """Grab basic system info - memory, disk, network.

    Nothing fancy, just the stuff you'd run manually when SSH'd in.
    """
    # Host info - date is important for correlating with logs later
    _capture(
        out_dir, "resource/host.txt",
        ["bash", "-lc", "date -Is; hostname; uname -a; uptime"],
        timeout=5,
    )

    # Memory - free for current state, vmstat for recent history
    _capture(
        out_dir, "resource/mem.txt",
        ["bash", "-lc", "free -h; echo; vmstat 1 5"],
        timeout=10,
    )

    # Disk
    _capture(
        out_dir, "resource/disk.txt",
        ["bash", "-lc", "df -h; echo; lsblk"],
        timeout=10,
    )

    # Network - ss needs root for process names but partial output is fine
    _capture(
        out_dir, "resource/net.txt",
        ["bash", "-lc", "ip a; echo; ip r; echo; ss -tulpn"],
        timeout=10,
    )

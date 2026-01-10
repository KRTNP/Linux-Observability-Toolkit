"""Systemd service data collector."""

from __future__ import annotations

import sys
from pathlib import Path

from toolkit.core.runner import run_cmd
from toolkit.core.bundle import write_text


def collect_systemd(out_dir: Path, unit: str):
    """Grab systemd info for a unit - status, properties, unit file."""

    # status - first thing everyone looks at
    r = run_cmd(["systemctl", "status", unit, "--no-pager"], timeout_sec=8)
    if r.returncode == 4:
        # Common mistake: forgetting .service suffix
        print(f"Warning: '{unit}' not found. Did you forget .service?", file=sys.stderr)
    write_text(out_dir / "systemd/status.txt", r.stdout + "\n\n" + r.stderr)

    # show - all properties, good for debugging restart loops
    r = run_cmd(["systemctl", "show", unit], timeout_sec=8)
    write_text(out_dir / "systemd/show.txt", r.stdout + "\n\n" + r.stderr)

    # cat - the actual unit file (sometimes different from what you think)
    r = run_cmd(["systemctl", "cat", unit], timeout_sec=8)
    write_text(out_dir / "systemd/unit.txt", r.stdout + "\n\n" + r.stderr)

"""Process snapshot collector."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from toolkit.core.runner import run_cmd
from toolkit.core.bundle import write_text


def _get_main_pid(unit):
    """Get MainPID from systemctl. Returns None if service isn't running."""
    r = run_cmd(["systemctl", "show", unit, "--property=MainPID"], timeout_sec=5)
    if r.returncode != 0:
        return None
    m = re.search(r"MainPID=(\d+)", r.stdout)
    if m:
        pid = int(m.group(1))
        return pid if pid > 0 else None
    return None


# TODO: Refactor this. Reading /proc directly is kinda sketchy but psutil
# is too heavy to add as a dep just for this. Also not sure if this breaks
# on hardened kernels with hidepid=2 - haven't tested that yet.
def _read_proc_file(pid, filename):
    """Read a /proc file. Returns error string if it fails."""
    # FIXME: racey - process could die between PID check and here
    proc_path = Path(f"/proc/{pid}/{filename}")
    try:
        return proc_path.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return f"[Permission denied - need root?]"
    except FileNotFoundError:
        return f"[Process {pid} gone]"
    except Exception as e:
        return f"[Error: {e}]"


def collect_process(out_dir: Path, unit: str):
    """Grab process info for the service's MainPID.

    Gets ps output, /proc limits, status, fd count. Useful for debugging
    resource exhaustion, fd leaks, that kind of thing.
    """
    pid = _get_main_pid(unit)

    if pid is None:
        write_text(
            out_dir / "process/snapshot.txt",
            f"No MainPID for {unit} - stopped or Type=oneshot?\n"
        )
        print(f"Note: No MainPID for '{unit}'", file=sys.stderr)
        return

    ts = datetime.now(timezone.utc).isoformat()

    lines = [
        f"# Process snapshot for {unit} (PID {pid})",
        f"# Captured: {ts}",
        f"# Warning: data might be inconsistent if process restarted mid-collection\n",
    ]

    # ps - basic info
    ps_r = run_cmd(
        ["ps", "-p", str(pid), "-o", "pid,ppid,user,%cpu,%mem,vsz,rss,stat,start,time,cmd"],
        timeout_sec=5,
    )
    lines.append("## ps\n")
    lines.append(ps_r.stdout or ps_r.stderr or "[failed]\n")
    lines.append("\n")

    # /proc limits - for debugging "too many open files" etc
    lines.append(f"## /proc/{pid}/limits\n")
    lines.append(_read_proc_file(pid, "limits"))
    lines.append("\n")

    # /proc status - memory breakdown, threads, etc
    lines.append(f"## /proc/{pid}/status\n")
    lines.append(_read_proc_file(pid, "status"))
    lines.append("\n")

    # fd count - just the count, listing all would be huge
    try:
        fd_count = len(list(Path(f"/proc/{pid}/fd").iterdir()))
        lines.append(f"## Open fds: {fd_count}\n")
    except PermissionError:
        lines.append("## Open fds: [need root]\n")
    except FileNotFoundError:
        lines.append("## Open fds: [process gone]\n")

    write_text(out_dir / "process/snapshot.txt", "".join(lines))

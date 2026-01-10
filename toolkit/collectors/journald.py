"""Journald log collector."""

from __future__ import annotations

import sys
from pathlib import Path

from toolkit.core.runner import run_cmd
from toolkit.core.bundle import write_text


def collect_journald(out_dir: Path, unit: str, since: str, lines: int,
                     redact=False, redact_patterns=None, redact_whitelist=None):
    """Grab logs via journalctl.

    NOTE: Be careful with 'lines' param on busy services -
    I once froze a box trying to pull 500k lines without --no-pager. Lesson learned.
    """
    r = run_cmd(
        [
            "journalctl",
            "-u", unit,
            "--since", since,
            "--no-pager",  # seriously, don't remove this
            "-n", str(lines),
            "--output=short-iso",
        ],
        timeout_sec=15,
        max_bytes=5_000_000,
    )

    if r.returncode != 0 and "No entries" in r.stderr:
        print(
            f"Note: No journal entries for '{unit}' in the last {since}. "
            f"Service might be quiet or --since too short.",
            file=sys.stderr,
        )

    output = r.stdout + "\n\n" + r.stderr

    write_text(
        out_dir / "logs/journald.txt",
        output,
        redact=redact,
        patterns=redact_patterns,
        whitelist=redact_whitelist
    )

"""Bundle creation utilities."""

from __future__ import annotations

import json
import re
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Regex patterns for redacting secrets
# TODO: these probably have edge cases I haven't hit yet
DEFAULT_REDACT_PATTERNS = [
    r"(?i)(api[_-]?key|apikey)[=:\s]+['\"]?[\w\-]+['\"]?",
    r"(?i)(secret|password|passwd|pwd)[=:\s]+['\"]?[^\s'\"]+['\"]?",
    r"(?i)(token|bearer)[=:\s]+['\"]?[\w\-\.]+['\"]?",
    r"(?i)(aws_secret|aws_access)[=:\s]+['\"]?[\w\-]+['\"]?",
    r"://[^:]+:[^@]+@",  # basic auth in URLs
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")


def check_disk_space(path: str, min_mb: int = 500) -> tuple[bool, int]:
    """Check if there's enough disk space. Returns (ok, available_mb)."""
    try:
        # Create parent dir if needed so we can check its disk
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        stat = shutil.disk_usage(p)
        available_mb = stat.free // (1024 * 1024)
        return available_mb >= min_mb, available_mb
    except Exception:
        return True, -1


def redact_text(
    text: str,
    patterns: List[str] | None = None,
    whitelist: List[str] | None = None
) -> str:
    """Redact sensitive data from text using regex patterns.

    Args:
        text: Input text to redact
        patterns: Extra patterns to redact (on top of defaults)
        whitelist: Patterns to restore after redaction (false positive protection)

    Not bulletproof - always review output before sharing.
    """
    all_patterns = DEFAULT_REDACT_PATTERNS + (patterns or [])
    result = text

    # First pass: redact everything matching patterns
    for pattern in all_patterns:
        try:
            result = re.sub(pattern, "***REDACTED***", result)
        except re.error:
            continue

    # Second pass: restore whitelisted terms that got caught
    # Use case: "password_hash_algorithm=sha256" shouldn't be redacted
    if whitelist:
        for wl_pattern in whitelist:
            try:
                # Find in original, restore in result
                for match in re.finditer(wl_pattern, text):
                    original = match.group(0)
                    result = result.replace("***REDACTED***", original, 1)
            except re.error:
                continue

    return result


def make_bundle_dir(artifacts_dir: str, service_name: str) -> Path:
    """Create a new bundle directory."""
    base = Path(artifacts_dir).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    incident_id = f"{utc_stamp()}-{service_name}"
    p = base / incident_id
    p.mkdir(parents=True, exist_ok=False)
    return p


def write_text(
    path: Path,
    text: str,
    redact: bool = False,
    patterns: List[str] | None = None,
    whitelist: List[str] | None = None
) -> None:
    """Write text to a file, optionally redacting secrets."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if redact:
        text = redact_text(text, patterns, whitelist)
    path.write_text(text, encoding="utf-8", errors="replace")


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    """Write JSON to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def tar_gz(dir_path: Path) -> Path:
    """Create a tar.gz archive of a directory."""
    tar_path = dir_path.with_suffix(".tar.gz")
    with tarfile.open(tar_path, "w:gz") as tf:
        tf.add(dir_path, arcname=dir_path.name)
    return tar_path

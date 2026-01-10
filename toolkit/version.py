"""Version info for the toolkit."""

import subprocess

__version__ = "0.3.0"


def get_git_hash() -> str:
    """Try to get current git commit hash. Returns 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

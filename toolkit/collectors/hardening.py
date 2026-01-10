"""Hardening check collector - reports on systemd security settings.

Checks for common security hardening options in systemd units.
Output is a simple PASS/WARN/FAIL report, not a full audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from toolkit.core.runner import run_cmd
from toolkit.core.bundle import write_text, write_json


@dataclass
class CheckResult:
    name: str
    status: str  # PASS, WARN, FAIL
    message: str
    property_value: str = ""


def _check_bool_enabled(value: str, prop: str) -> tuple[str, str]:
    """Check if a boolean hardening option is enabled."""
    if value.lower() in ("yes", "true", "1"):
        return "PASS", f"{prop} is enabled"
    return "WARN", f"{prop} is not enabled (currently: {value})"


def _check_not_root(value: str) -> tuple[str, str]:
    if value and value != "root" and value != "0":
        return "PASS", f"Running as non-root user: {value}"
    return "WARN", f"Running as root (User={value or 'not set'})"


def _check_private_tmp(value: str) -> tuple[str, str]:
    return _check_bool_enabled(value, "PrivateTmp")


def _check_protect_system(value: str) -> tuple[str, str]:
    if value.lower() in ("strict", "full", "true", "yes"):
        return "PASS", f"ProtectSystem={value}"
    elif value.lower() == "false" or not value:
        return "WARN", "ProtectSystem is not set"
    return "PASS", f"ProtectSystem={value}"


def _check_protect_home(value: str) -> tuple[str, str]:
    if value.lower() in ("yes", "true", "read-only", "tmpfs"):
        return "PASS", f"ProtectHome={value}"
    return "WARN", f"ProtectHome is not set (home dirs accessible)"


def _check_no_new_privs(value: str) -> tuple[str, str]:
    return _check_bool_enabled(value, "NoNewPrivileges")


HARDENING_CHECKS: Dict[str, tuple[callable, str]] = {
    "User": (_check_not_root, "Running as non-root user"),
    "PrivateTmp": (_check_private_tmp, "Private /tmp namespace"),
    "ProtectSystem": (_check_protect_system, "Filesystem protection"),
    "ProtectHome": (_check_protect_home, "Home directory protection"),
    "NoNewPrivileges": (_check_no_new_privs, "Prevent privilege escalation"),
}


def _parse_systemctl_show(output: str) -> Dict[str, str]:
    props = {}
    for line in output.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            props[key.strip()] = value.strip()
    return props


def _get_distro_info() -> str:
    """Try to detect Linux distro. Returns empty string if can't detect."""
    try:
        # Try /etc/os-release first (works on most modern distros)
        os_release = Path("/etc/os-release")
        if os_release.exists():
            content = os_release.read_text()
            for line in content.splitlines():
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip('"')
    except Exception:
        pass
    return ""


def collect_hardening(out_dir: Path, unit: str, options: Dict[str, Any]) -> None:
    """Run hardening checks and write report."""
    r = run_cmd(["systemctl", "show", unit], timeout_sec=8)
    if r.returncode != 0:
        write_text(
            out_dir / "hardening/report.txt",
            f"Failed to get unit properties: {r.stderr}\n"
        )
        return

    props = _parse_systemctl_show(r.stdout)
    results: list[CheckResult] = []

    for prop_name, (check_fn, description) in HARDENING_CHECKS.items():
        value = props.get(prop_name, "")
        status, message = check_fn(value)
        results.append(CheckResult(
            name=description,
            status=status,
            message=message,
            property_value=value,
        ))

    # Detect distro for context
    distro = _get_distro_info()

    # Generate report
    lines = [
        f"# Hardening Report for {unit}",
        f"# This is a basic check, not a full security audit",
    ]

    if distro:
        lines.append(f"# Distro: {distro}")

    lines.append("")
    lines.append("# NOTE: Default values may vary between distros (RHEL vs Ubuntu vs Debian).")
    lines.append("# Some services may legitimately need root or access to /home.\n")

    pass_count = sum(1 for r in results if r.status == "PASS")
    warn_count = sum(1 for r in results if r.status == "WARN")
    fail_count = sum(1 for r in results if r.status == "FAIL")

    lines.append(f"Summary: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL\n")
    lines.append("-" * 60 + "\n")

    for result in results:
        symbol = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]"}[result.status]
        lines.append(f"{symbol} {result.name}")
        lines.append(f"    {result.message}\n")

    if warn_count > 0:
        lines.append("\n" + "=" * 60)
        lines.append("RECOMMENDATIONS")
        lines.append("=" * 60 + "\n")
        lines.append("Consider adding these to your unit file:\n")
        lines.append("  [Service]")
        for result in results:
            if result.status == "WARN":
                if "non-root" in result.name.lower():
                    lines.append("  User=nobody  # or a dedicated service user")
                elif "PrivateTmp" in result.message:
                    lines.append("  PrivateTmp=yes")
                elif "ProtectSystem" in result.message:
                    lines.append("  ProtectSystem=strict")
                elif "ProtectHome" in result.message:
                    lines.append("  ProtectHome=yes")
                elif "NoNewPrivileges" in result.message:
                    lines.append("  NoNewPrivileges=yes")
        lines.append("")

    write_text(out_dir / "hardening/report.txt", "\n".join(lines))

    json_results = {
        "unit": unit,
        "distro": distro,
        "summary": {"pass": pass_count, "warn": warn_count, "fail": fail_count},
        "checks": [
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "property_value": r.property_value,
            }
            for r in results
        ],
    }
    write_json(out_dir / "hardening/report.json", json_results)

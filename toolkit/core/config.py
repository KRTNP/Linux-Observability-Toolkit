"""Configuration loading with defaults and validation."""

from __future__ import annotations

from typing import Any, Dict

import yaml

DEFAULTS: Dict[str, Any] = {
    "output": {
        "artifacts_dir": "/var/tmp/incident-bundles",
        "min_disk_mb": 500,  # warn if less than this
    },
    "logs": {"since": "60 min ago", "lines": 5000},
    "collect": {
        "systemd": True,
        "journald": True,
        "resource": True,
        "process": True,
        "hardening": False,
    },
    "redact": {
        "enabled": False,  # opt-in, can slow things down
        "patterns": [],    # extra patterns on top of defaults
        "whitelist": [],   # patterns to NOT redact (false positive protection)
    },
    "collector_options": {
        "journald": {
            "output_format": "short-iso",
        },
        "resource": {
            "vmstat_samples": 5,
        },
        "process": {
            "include_fd_list": False,
        },
        "hardening": {
            "fail_on_warn": False,
        },
    },
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dicts."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str) -> Dict[str, Any]:
    """Load config from YAML, merged with defaults."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    cfg = deep_merge(DEFAULTS, raw)

    # Validate required field
    unit = (cfg.get("service") or {}).get("unit")
    if not unit:
        raise ValueError("config.service.unit is required")

    # Auto-derive name from unit if not set
    name = (cfg.get("service") or {}).get("name") or unit.replace(".service", "")
    cfg["service"]["name"] = name

    return cfg

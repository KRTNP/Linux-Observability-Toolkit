"""Simple metrics for tracking bundle collection.

Writes metrics to a file that Prometheus node_exporter textfile collector can scrape.
No extra dependencies needed - just write to /var/lib/node_exporter/textfile_collector/
"""

from __future__ import annotations

import time
from pathlib import Path

# Default location for node_exporter textfile collector
# Change this if your setup is different
METRICS_DIR = Path("/var/lib/node_exporter/textfile_collector")
METRICS_FILE = "toolkit.prom"


def write_metrics(service: str, collectors_run: list, collectors_failed: list,
                  duration_sec: float, bundle_size_bytes: int = 0):
    """Write Prometheus-format metrics to textfile.

    Uses node_exporter's textfile collector - no need to run a separate exporter.
    Just make sure node_exporter is configured with --collector.textfile.directory
    """
    metrics_path = METRICS_DIR / METRICS_FILE

    # Skip if directory doesn't exist (node_exporter not configured)
    if not METRICS_DIR.exists():
        return

    timestamp = int(time.time() * 1000)

    lines = [
        "# HELP toolkit_collection_total Total bundle collections",
        "# TYPE toolkit_collection_total counter",
        f'toolkit_collection_total{{service="{service}"}} 1',
        "",
        "# HELP toolkit_collection_duration_seconds Time to collect bundle",
        "# TYPE toolkit_collection_duration_seconds gauge",
        f'toolkit_collection_duration_seconds{{service="{service}"}} {duration_sec:.2f}',
        "",
        "# HELP toolkit_collectors_success Number of collectors that succeeded",
        "# TYPE toolkit_collectors_success gauge",
        f'toolkit_collectors_success{{service="{service}"}} {len(collectors_run)}',
        "",
        "# HELP toolkit_collectors_failed Number of collectors that failed",
        "# TYPE toolkit_collectors_failed gauge",
        f'toolkit_collectors_failed{{service="{service}"}} {len(collectors_failed)}',
        "",
        "# HELP toolkit_bundle_size_bytes Size of generated bundle",
        "# TYPE toolkit_bundle_size_bytes gauge",
        f'toolkit_bundle_size_bytes{{service="{service}"}} {bundle_size_bytes}',
        "",
        "# HELP toolkit_last_collection_timestamp_seconds Last collection time",
        "# TYPE toolkit_last_collection_timestamp_seconds gauge",
        f'toolkit_last_collection_timestamp_seconds{{service="{service}"}} {time.time():.0f}',
    ]

    try:
        metrics_path.write_text("\n".join(lines) + "\n")
    except (PermissionError, OSError):
        # Can't write metrics, not a big deal
        pass

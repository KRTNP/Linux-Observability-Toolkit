"""CLI entry point."""

from __future__ import annotations

import argparse
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from toolkit.core.config import load_config
from toolkit.core.bundle import make_bundle_dir, write_json, tar_gz, check_disk_space
from toolkit.collectors.systemd import collect_systemd
from toolkit.collectors.journald import collect_journald
from toolkit.collectors.resource import collect_resource
from toolkit.collectors.process import collect_process
from toolkit.collectors.hardening import collect_hardening
from toolkit.version import __version__, get_git_hash


def main():
    p = argparse.ArgumentParser(prog="toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    inc = sub.add_parser("incident")
    inc_sub = inc.add_subparsers(dest="subcmd", required=True)

    coll = inc_sub.add_parser("collect")
    coll.add_argument("--config", required=True)
    coll.add_argument("--since", default=None)
    coll.add_argument("--lines", type=int, default=None)
    coll.add_argument("--redact", action="store_true", help="Scrub secrets from logs")
    coll.add_argument("--serial", action="store_true", help="Don't parallelize (for debugging)")

    args = p.parse_args()

    if args.cmd == "incident" and args.subcmd == "collect":
        cfg = load_config(args.config)
        unit = cfg["service"]["unit"]
        svc = cfg["service"]["name"]
        artifacts_dir = cfg["output"]["artifacts_dir"]
        since = args.since or cfg["logs"]["since"]
        lines = args.lines or cfg["logs"]["lines"]

        # Sanity check - don't fill up the disk
        ok, avail = check_disk_space(artifacts_dir)
        if not ok:
            print(f"WARNING: Low disk ({avail}MB free)", file=sys.stderr)

        out_dir = make_bundle_dir(artifacts_dir, svc)

        # Redaction settings
        redact_cfg = cfg.get("redact", {})
        do_redact = args.redact or redact_cfg.get("enabled", False)
        extra_patterns = redact_cfg.get("patterns", [])
        whitelist = redact_cfg.get("whitelist", [])

        # Queue up collector jobs
        jobs = []

        if cfg["collect"].get("systemd", True):
            jobs.append(("systemd", lambda: collect_systemd(out_dir, unit)))

        if cfg["collect"].get("journald", True):
            # Need default args in lambda to avoid closure issues (learned this the hard way)
            jobs.append(("journald", lambda u=unit, s=since, l=lines:
                collect_journald(out_dir, u, s, l, redact=do_redact,
                                redact_patterns=extra_patterns, redact_whitelist=whitelist)))

        if cfg["collect"].get("resource", True):
            jobs.append(("resource", lambda: collect_resource(out_dir)))

        if cfg["collect"].get("process", True):
            jobs.append(("process", lambda u=unit: collect_process(out_dir, u)))

        if cfg["collect"].get("hardening", False):
            opts = cfg.get("collector_options", {}).get("hardening", {})
            jobs.append(("hardening", lambda u=unit, o=opts: collect_hardening(out_dir, u, o)))

        # Run em - parallel by default, way faster for I/O bound stuff
        done = []
        failed = []

        if args.serial or len(jobs) <= 1:
            for name, fn in jobs:
                try:
                    fn()
                    done.append(name)
                except Exception as e:
                    print(f"'{name}' failed: {e}", file=sys.stderr)
                    failed.append(name)
        else:
            # Parallel - usually finishes in half the time
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(fn): name for name, fn in jobs}
                for f in as_completed(futures):
                    name = futures[f]
                    try:
                        f.result()
                        done.append(name)
                    except Exception as e:
                        print(f"'{name}' failed: {e}", file=sys.stderr)
                        failed.append(name)

        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "toolkit_version": __version__,
            "toolkit_git": get_git_hash(),
            "service": {"name": svc, "unit": unit},
            "host": socket.gethostname(),
            "args": {"since": since, "lines": lines, "redact": do_redact},
            "collectors": done,
            "collectors_failed": failed,
        }

        write_json(out_dir / "meta.json", meta)

        tgz = tar_gz(out_dir)
        print(str(tgz))

        return 1 if failed else 0

    return 2

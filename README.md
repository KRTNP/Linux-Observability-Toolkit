# Linux Observability Toolkit

CLI tool for grabbing incident data from Linux boxes into a single bundle.

## Why I Built This

Tired of SSHing into a crashed server and running the same `journalctl`, `systemctl status`, `free -h` dance every time. This bundles everything into one tarball so you can analyze it later (or send it to someone else to look at).

## Requirements

- Python 3.10+
- Linux with systemd (Ubuntu, Debian, CentOS, RHEL, Fedora, etc.)
- The usual suspects: `systemctl`, `journalctl`, `bash`, `ip`, `ss`, `df`, `free`, `lsblk`

**Won't work on:** Alpine (no systemd), WSL1 (fake systemd), old RHEL 6 boxes

## Quick Start

```bash
git clone <repo>
cd linux-observability-toolkit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy and edit a config for your service:

```bash
cp config/services/nginx.yaml config/services/myapp.yaml
# edit myapp.yaml with your service details
```

Run it:

```bash
python -m toolkit incident collect --config config/services/myapp.yaml
```

With log redaction (scrubs passwords, API keys, tokens):

```bash
python -m toolkit incident collect --config config/services/myapp.yaml --redact
```

Override log settings:

```bash
python -m toolkit incident collect --config config/services/myapp.yaml --since "2h" --lines 20000
```

## What You Get

```
/var/tmp/incident-bundles/20250109-123456Z-myapp/
├── systemd/
│   ├── status.txt    # systemctl status
│   ├── show.txt      # systemctl show
│   └── unit.txt      # unit file contents
├── logs/
│   └── journald.txt  # journal logs (optionally redacted)
├── resource/
│   ├── host.txt      # hostname, uname, uptime
│   ├── mem.txt       # free, vmstat
│   ├── disk.txt      # df, lsblk
│   └── net.txt       # ip a, ip r, ss -tulpn
├── process/
│   └── snapshot.txt  # ps, /proc limits, fd count
├── hardening/        # (if enabled)
│   ├── report.txt    # PASS/WARN/FAIL
│   └── report.json
├── meta.json         # includes toolkit version, git hash
└── *.tar.gz
```

## Collectors

| Collector | Default | What it grabs |
|-----------|---------|---------------|
| `systemd` | on | unit status, properties, unit file |
| `journald` | on | service logs (supports redaction) |
| `resource` | on | memory, disk, network info |
| `process` | on | MainPID info, /proc limits, fd count |
| `hardening` | **off** | security check report |

## Log Redaction

Bundles can contain secrets (API keys in error logs, etc). Use `--redact` to scrub common patterns:

```bash
python -m toolkit incident collect --config ... --redact
```

Or enable in config:

```yaml
redact:
  enabled: true
  patterns:
    # extra patterns on top of defaults
    - "MY_SECRET_\\w+"
```

Default patterns catch: `api_key=`, `password=`, `token=`, `secret=`, `bearer`, basic auth in URLs.

**Still review the bundle before sharing** - regex isn't perfect.

## Safety Features

- **Disk space check**: Warns if < 500MB free before collecting
- **Output limits**: Commands limited to 2MB stdout/stderr
- **Timeout**: Each command has a timeout (no hanging on stuck processes)

## Config Options

```yaml
service:
  name: myapp
  unit: myapp.service

output:
  artifacts_dir: /var/tmp/incident-bundles
  min_disk_mb: 500    # warn below this

logs:
  since: "30 min ago"
  lines: 10000

collect:
  systemd: true
  journald: true
  resource: true
  process: true
  hardening: false

redact:
  enabled: false
  patterns: []        # extra regex patterns
```

## Runbooks

See `runbooks/` for deployment procedures:
- `deploy.md` - deploy with pre/post bundle collection
- `rollback.md` - rollback with evidence preservation

## Troubleshooting

**Collector fails on old CentOS 7 boxes**

Some systemd features are missing on older distros. Just disable the problematic collector in your config and move on:

```yaml
collect:
  hardening: false  # doesn't work great on centos 7
```

**"No journal entries" warning**

Usually means the service is just quiet, or your `--since` window is too short. Try `--since "2h"` or check if the service actually logs to journald (some apps log to files instead).

**Permission denied on /proc stuff**

Run as root, or accept that you won't get process details. The tool won't crash, it'll just show `[need root]` in the output.

**Bundle is huge**

Lower the `lines` setting in your config. Default is 5000 which is usually fine, but busy services can generate a lot.

## Known Issues / TODO

- Redaction regex might miss weird formats or false-positive on legit data - always review before sharing
- `lsof` not implemented - just counting fds for now
- RHEL/CentOS: postgres unit is `postgresql-XX.service`, not `postgresql.service`
- Haven't tested on every distro, YMMV on Arch/Gentoo/etc
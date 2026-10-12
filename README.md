# Linux Observability Toolkit

A CLI tool that grabs incident data from a Linux box and packs it into one bundle.

## Why I built this

I got tired of SSHing into a crashed server and running the same `journalctl`, `systemctl status`, `free -h` routine every time. This does all of it in one go and gives you a tarball you can dig through later, or hand to someone else.

## Requirements

- Python 3.10+
- Linux with systemd (Ubuntu, Debian, CentOS, RHEL, Fedora, etc.)
- The usual suspects: `systemctl`, `journalctl`, `bash`, `ip`, `ss`, `df`, `free`, `lsblk`

It won't work on Alpine (no systemd), WSL1 (fake systemd), or old RHEL 6 boxes.

## Quick start

```bash
git clone <repo>
cd linux-observability-toolkit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy one of the example configs and edit it for your service:

```bash
cp config/services/nginx.yaml config/services/myapp.yaml
# edit myapp.yaml with your service details
```

Run it:

```bash
python -m toolkit incident collect --config config/services/myapp.yaml
```

Add `--redact` to scrub passwords, API keys, and tokens from the logs:

```bash
python -m toolkit incident collect --config config/services/myapp.yaml --redact
```

Or override the log window and line count:

```bash
python -m toolkit incident collect --config config/services/myapp.yaml --since "2h" --lines 20000
```

## What you get

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
| `hardening` | off | security check report |

## Log redaction

Bundles can end up with secrets in them, like an API key that got dumped into an error log. `--redact` scrubs the common patterns:

```bash
python -m toolkit incident collect --config ... --redact
```

You can also turn it on in the config and add your own patterns:

```yaml
redact:
  enabled: true
  patterns:
    # extra patterns on top of defaults
    - "MY_SECRET_\\w+"
```

The defaults catch `api_key=`, `password=`, `token=`, `secret=`, `bearer`, and basic auth in URLs.

Look through the bundle yourself before you share it anyway. Regex isn't perfect.

## Safety

The tool warns you if there's less than 500MB of free disk before it starts collecting. Each command's stdout and stderr are capped at 2MB, and every command has a timeout, so a stuck process won't hang the whole run.

## Config

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

`runbooks/` has two deployment procedures:

- `deploy.md`: deploy with a bundle collected before and after
- `rollback.md`: roll back while keeping the evidence

## Troubleshooting

### A collector fails on old CentOS 7 boxes

Older distros are missing some systemd features. Turn off the collector that's failing and move on:

```yaml
collect:
  hardening: false  # doesn't work great on centos 7
```

### "No journal entries" warning

Usually the service is just quiet, or your `--since` window is too short. Try `--since "2h"`, and check that the service actually logs to journald. Some apps write to their own log files instead.

### Permission denied on /proc

Run it as root, or live without the process details. The tool won't crash. You'll just see `[need root]` in the output.

### The bundle is huge

Lower `lines` in your config. The default is 5000, which is usually fine, but a busy service can log a lot.

## Known issues / TODO

- Redaction can miss weird formats, or redact stuff that isn't actually a secret. Review before sharing.
- No `lsof` yet. It only counts fds for now.
- On RHEL/CentOS the postgres unit is `postgresql-XX.service`, not `postgresql.service`.
- I haven't tested it on every distro. YMMV on Arch, Gentoo, etc.

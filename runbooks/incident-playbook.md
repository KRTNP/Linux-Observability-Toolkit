# Incident Response Playbook

Quick reference for when things go wrong. Keep this open during incidents.

---

## Step 1: Collect Evidence (First 2 minutes)

**Before you touch anything**, grab a bundle:

```bash
python -m toolkit incident collect --config config/services/<service>.yaml --redact
```

Save the output path. You'll need this for the post-mortem.

---

## Step 2: Quick Triage (Next 3 minutes)

Extract and scan the bundle:

```bash
tar xzf /var/tmp/incident-bundles/<bundle>.tar.gz
cd <bundle>
```

**Check in this order:**

| File | What to look for |
|------|------------------|
| `systemd/status.txt` | Is it running? Recent restarts? Exit code? |
| `logs/journald.txt` | Last 50 lines - any obvious errors? |
| `resource/mem.txt` | OOM? Check "available" in `free -h` output |
| `resource/disk.txt` | Disk full? Check `df -h` for 100% |
| `process/snapshot.txt` | FD exhaustion? Check open fds count |

---

## Step 3: Common Fixes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `status: failed` | Crash/OOM | Check logs, restart: `systemctl restart <svc>` |
| `status: activating` stuck | Startup hang | Kill and restart, check deps |
| Disk 100% | Logs/temp files | `journalctl --vacuum-size=500M`, clear old files |
| High memory | Memory leak | Restart service, file bug for later |
| "Too many open files" | FD leak | Restart, check `LimitNOFILE` in unit |
| Connection refused | Not listening | Check if process is up, port binding |

---

## Step 4: Escalation

**Escalate if:**
- [ ] Service won't stay up after 2 restarts
- [ ] Data loss suspected
- [ ] Multiple services affected
- [ ] You're not sure what's happening

**Before escalating, have ready:**
1. Bundle path (from Step 1)
2. What you've tried
3. When it started
4. Impact scope (users affected?)

---

## Step 5: Resolution & Cleanup

After service is stable:

```bash
# Collect post-fix bundle for comparison
python -m toolkit incident collect --config config/services/<service>.yaml

# Note both bundle paths for post-mortem
```

**Don't forget:**
- [ ] Update status page / notify stakeholders
- [ ] Create ticket for root cause analysis
- [ ] Schedule post-mortem if impact was significant

---

## Quick Commands Reference

```bash
# Restart service
sudo systemctl restart <service>

# Check recent logs
journalctl -u <service> -n 100 --no-pager

# Check disk space
df -h

# Check memory
free -h

# Check what's using memory
ps aux --sort=-%mem | head -20

# Check open ports
ss -tulpn | grep <port>

# Kill stuck process
sudo kill -9 <pid>
```

---

**Remember:** Collect first, fix second. Bundles are your evidence.

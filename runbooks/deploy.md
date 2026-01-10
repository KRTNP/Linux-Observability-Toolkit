# Deploy Runbook

Standard deployment procedure with evidence collection.

## Pre-Deploy

**Collect baseline bundle BEFORE making changes.** If something goes wrong, you'll want to compare before/after.

```bash
# Capture current state
python -m toolkit incident collect --config config/services/<service>.yaml

# Note the bundle path for later comparison
# Example: /var/tmp/incident-bundles/20250109-120000Z-myapp.tar.gz
```

**Review the baseline:**
- Check `systemd/status.txt` - service should be active
- Check `resource/mem.txt` - note current memory usage
- Check `process/snapshot.txt` - note open FD count

## Deploy Steps

1. **Stop service (if needed)**
   ```bash
   sudo systemctl stop <service>
   ```

2. **Deploy new version**
   ```bash
   # Your deployment method here
   # Examples:
   # - cp/rsync new files
   # - apt/yum upgrade
   # - docker pull && docker-compose up -d
   # - ansible-playbook deploy.yml
   ```

3. **Start/restart service**
   ```bash
   sudo systemctl start <service>
   # or
   sudo systemctl restart <service>
   ```

4. **Quick health check**
   ```bash
   systemctl status <service>
   journalctl -u <service> -n 20 --no-pager
   ```

## Post-Deploy

**Collect post-deploy bundle.** Compare with pre-deploy to spot issues.

```bash
python -m toolkit incident collect --config config/services/<service>.yaml
```

**What to check:**
- `systemd/status.txt` - is it running?
- `logs/journald.txt` - any errors during startup?
- `process/snapshot.txt` - memory usage similar to before?
- `hardening/report.txt` (if enabled) - any new warnings?

## If Something Goes Wrong

Don't panic. You have the pre-deploy bundle.

1. Collect current (broken) state:
   ```bash
   python -m toolkit incident collect --config config/services/<service>.yaml
   ```

2. Compare logs between pre-deploy and post-deploy bundles

3. If rollback needed, see [rollback.md](rollback.md)

## Evidence Retention

Keep bundles for at least:
- Pre/post deploy: 30 days (or until next deploy)
- Incident bundles: 90 days (or per your retention policy)

```bash
# Clean up old bundles (older than 30 days)
find /var/tmp/incident-bundles -name "*.tar.gz" -mtime +30 -delete
```

# Rollback Runbook

When a deploy goes wrong and you need to go back.

## Before You Rollback

**Capture the broken state first.** You'll need this for the post-mortem.

```bash
python -m toolkit incident collect --config config/services/<service>.yaml

# Save this bundle path - it's evidence
```

**Quick diagnosis from the bundle:**
```bash
# Extract and check logs
tar xzf /var/tmp/incident-bundles/<bundle>.tar.gz
grep -i error <bundle>/logs/journald.txt | tail -20
grep -i fail <bundle>/logs/journald.txt | tail -20
```

## Rollback Steps

### Option A: Package-based rollback

If you deployed via apt/yum:

```bash
# Debian/Ubuntu
apt list --installed <package> -a  # see available versions
sudo apt install <package>=<previous-version>

# RHEL/CentOS
yum history list <package>
sudo yum history undo <transaction-id>
```

### Option B: File-based rollback

If you have a backup:

```bash
sudo systemctl stop <service>
# Restore previous files
sudo cp -r /backup/<service>/* /path/to/service/
sudo systemctl start <service>
```

### Option C: Container rollback

```bash
docker pull <image>:<previous-tag>
docker-compose down
docker-compose up -d
```

### Option D: Git-based rollback

```bash
cd /path/to/app
git log --oneline -5  # find the good commit
git checkout <good-commit>
sudo systemctl restart <service>
```

## After Rollback

**Verify the rollback worked:**

```bash
systemctl status <service>
journalctl -u <service> -n 20 --no-pager
```

**Collect post-rollback bundle:**

```bash
python -m toolkit incident collect --config config/services/<service>.yaml
```

**Compare with pre-deploy bundle** - things should look similar to before the failed deploy.

## Post-Mortem Checklist

You now have 3 bundles:
1. **Pre-deploy** (baseline, working state)
2. **Post-deploy** (broken state)
3. **Post-rollback** (should match #1)

For the post-mortem:
- [ ] Diff the journal logs between #1 and #2
- [ ] Check `systemd/show.txt` for restart count changes
- [ ] Compare `process/snapshot.txt` memory/fd usage
- [ ] Note any `hardening/report.txt` differences
- [ ] Document root cause
- [ ] Create ticket for proper fix

## Emergency Contacts

*Add your team's escalation contacts here:*

```
# On-call: <phone/slack>
# Infra lead: <email>
# Manager: <email>
```

# Monitoring Setup

Optional Prometheus + Grafana integration for tracking bundle collections.

## How It Works

The toolkit writes metrics to a text file that node_exporter's textfile collector picks up. No extra daemons needed.

```
toolkit collect → writes to /var/lib/node_exporter/textfile_collector/toolkit.prom
                            ↓
node_exporter textfile collector scrapes it
                            ↓
Prometheus scrapes node_exporter
                            ↓
Grafana shows dashboard
```

## Setup

### 1. Configure node_exporter

Make sure node_exporter has the textfile collector enabled:

```bash
# In systemd unit or command line
node_exporter --collector.textfile.directory=/var/lib/node_exporter/textfile_collector
```

Create the directory:

```bash
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo chown <your-user> /var/lib/node_exporter/textfile_collector
```

### 2. Import Grafana Dashboard

1. Open Grafana → Dashboards → Import
2. Upload `grafana-dashboard.json` or paste its contents
3. Select your Prometheus data source
4. Save

### 3. Add Alerting Rules

Copy the alert rules to Prometheus:

```bash
sudo cp prometheus-alerts.yml /etc/prometheus/rules.d/
sudo systemctl reload prometheus
```

Or include in `prometheus.yml`:

```yaml
rule_files:
  - "/path/to/prometheus-alerts.yml"
```

## Metrics Exposed

| Metric | Type | Description |
|--------|------|-------------|
| `toolkit_collection_total` | counter | Number of collections |
| `toolkit_collection_duration_seconds` | gauge | Time to collect bundle |
| `toolkit_collectors_success` | gauge | Collectors that succeeded |
| `toolkit_collectors_failed` | gauge | Collectors that failed |
| `toolkit_bundle_size_bytes` | gauge | Bundle tarball size |
| `toolkit_last_collection_timestamp_seconds` | gauge | Unix timestamp of last collection |

All metrics have a `service` label.

## Alerts

| Alert | Severity | Trigger |
|-------|----------|---------|
| `ToolkitCollectorFailed` | warning | Any collector failed |
| `ToolkitCollectionSlow` | warning | Collection > 60s |
| `ToolkitBundleTooLarge` | warning | Bundle > 50MB |
| `ToolkitNoRecentCollection` | info | No collection in 24h |

## Cron Example

Run periodic collections and let Prometheus track them:

```bash
# /etc/cron.d/toolkit
*/30 * * * * root python3 -m toolkit incident collect --config /etc/toolkit/nginx.yaml 2>&1 | logger -t toolkit
```

This collects every 30 minutes and logs output to syslog.

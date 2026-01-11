#!/bin/bash
set -e

echo "=== Building Docker image ==="
docker build -t linux-observability-toolkit:latest .

echo ""
echo "=== Testing toolkit help ==="
docker run --rm linux-observability-toolkit:latest --help

echo ""
echo "=== Running collect (nginx) ==="
docker run --rm \
    -v /var/tmp/incident-bundles:/var/tmp/incident-bundles \
    linux-observability-toolkit:latest \
    incident collect --config config/services/nginx.yaml

echo ""
echo "=== Done! ==="
echo "Bundles saved to: /var/tmp/incident-bundles/"
ls -la /var/tmp/incident-bundles/*.tar.gz | tail -3

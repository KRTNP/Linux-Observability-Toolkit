FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for collecting system info
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    iproute2 \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt ./
COPY toolkit/ ./toolkit/
COPY config/ ./config/

# Install Python dependencies
RUN pip install --no-cache-dir pyyaml>=6.0

# Create output directory
RUN mkdir -p /var/tmp/incident-bundles

# Set entrypoint
ENTRYPOINT ["python3", "-m", "toolkit"]
CMD ["--help"]

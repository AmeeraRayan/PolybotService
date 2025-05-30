#!/bin/bash
if ! command -v otelcol &> /dev/null; then
  echo "📡 Installing OpenTelemetry Collector..."
  sudo yum update
  sudo yum -y install wget systemctl
  wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.127.0/otelcol_0.127.0_linux_amd64.rpm
  sudo rpm -ivh otelcol_0.127.0_linux_amd64.rpm
else
  echo "✅ OpenTelemetry Collector already installed, skipping install."
fi

echo "⚙️ Writing OpenTelemetry Collector config to /etc/otelcol/config.yaml..."
sudo tee /etc/otelcol/config.yaml > /dev/null <<EOL
receivers:
  hostmetrics:
    collection_interval: 15s
    scrapers:
      cpu:
      memory:
      disk:
      filesystem:
      load:
      network:
      processes:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    metrics:
      receivers: [hostmetrics]
      exporters: [prometheus]
EOL

sudo systemctl restart otelcol

# Copy the polybot-dev service file
sudo cp polybot-dev.service /etc/systemd/system/


# Reload systemd and restart both services
sudo systemctl daemon-reload

sleep 10
sudo systemctl restart polybot-dev.service
sudo systemctl enable polybot-dev.service

# Check if polybot-dev is running
if ! systemctl is-active --quiet polybot-dev.service; then
  echo "✗ polybot-dev.service is not running."
  sudo systemctl status polybot-dev.service --no-pager
  exit 1
fi

echo "✓ Both Polybot-Dev and Ngrok services are running successfully!"
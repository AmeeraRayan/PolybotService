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

# Copy the polybot service file
sudo cp polybot.service /etc/systemd/system/

# Reload daemon and restart both services
sudo systemctl daemon-reload

sleep 10
sudo systemctl restart polybot.service
sudo systemctl enable polybot.service

# Check if polybot is running
if ! systemctl is-active --quiet polybot.service; then
  echo "✗ polybot.service is not running."
  sudo systemctl status polybot.service --no-pager
  exit 1
fi


echo "✓ Both Polybot and Ngrok services are running successfully!"
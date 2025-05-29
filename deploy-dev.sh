#!/bin/bash

# Copy the polybot-dev service file
sudo cp polybot-dev.service /etc/systemd/system/

# Copy the ngrok service file (we can reuse the same one for dev)
sudo cp ngrok.service /etc/systemd/system/

# Reload systemd and restart both services
sudo systemctl daemon-reload

sudo systemctl restart ngrok.service
sudo systemctl enable ngrok.service
sleep 10
sudo systemctl restart polybot-dev.service
sudo systemctl enable polybot-dev.service

# Check if polybot-dev is running
if ! systemctl is-active --quiet polybot-dev.service; then
  echo "✗ polybot-dev.service is not running."
  sudo systemctl status polybot-dev.service --no-pager
  exit 1
fi

# Check if ngrok is running
if ! systemctl is-active --quiet ngrok.service; then
  echo "✗ ngrok.service is not running."
  sudo systemctl status ngrok.service --no-pager
  exit 1
fi

echo "✓ Both Polybot-Dev and Ngrok services are running successfully!"
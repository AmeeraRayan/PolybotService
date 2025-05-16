#!/bin/bash

# Copy the polybot service file
sudo cp polybot.service /etc/systemd/system/

# Copy the ngrok service file
sudo cp ngrok.service /etc/systemd/system/

# Reload daemon and restart both services
sudo systemctl daemon-reload

sudo systemctl restart ngrok.service
sudo systemctl enable ngrok.service

sudo systemctl restart polybot.service
sudo systemctl enable polybot.service

# Check if polybot is running
if ! systemctl is-active --quiet polybot.service; then
  echo "✗ polybot.service is not running."
  sudo systemctl status polybot.service --no-pager
  exit 1
fi

# Check if ngrok is running
if ! systemctl is-active --quiet ngrok.service; then
  echo "✗ ngrok.service is not running."
  sudo systemctl status ngrok.service --no-pager
  exit 1
fi

echo "✓ Both Polybot and Ngrok services are running successfully!"
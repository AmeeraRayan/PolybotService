#!/bin/bash

cd ~/PolybotService

# Stop existing service if exists
sudo systemctl stop polybot.service || true

# Pull latest code
git pull origin main

# Create venv if doesn't exist
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart polybot.service
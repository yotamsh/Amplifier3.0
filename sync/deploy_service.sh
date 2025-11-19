#!/bin/bash
#
# Deploy HumanAmplifier systemd service
# Run this ON THE PI from the project directory
#

set -e  # Exit on any error

echo "Deploying HumanAmplifier service..."

# Copy service file
sudo cp sync/humanamp.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# If service is already running, restart it
if systemctl is-active --quiet humanamp.service; then
    echo "Service is running - restarting..."
    sudo systemctl restart humanamp.service
else
    echo "Enabling and starting service..."
    sudo systemctl enable humanamp.service
    sudo systemctl start humanamp.service
fi

# Show status
echo ""
sudo systemctl status humanamp.service --no-pager

echo ""
echo "Done! View logs with: sudo journalctl -u humanamp.service -f"


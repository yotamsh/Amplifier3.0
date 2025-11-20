# HumanAmplifier systemd Service Deployment

This guide explains how to deploy the HumanAmplifier system as a systemd service that auto-starts on boot and automatically restarts on crashes.

## Overview

The systemd service provides:
- ✅ **Auto-start on boot** - System starts when Pi powers on
- ✅ **Auto-restart on crash** - Crashes are auto-recovered in 10 seconds
- ✅ **Full logging** - All stdout/stderr captured via journalctl
- ✅ **Graceful shutdown** - Proper signal handling (SIGTERM)
- ✅ **Process management** - Easy start/stop/restart control
- ✅ **Status monitoring** - Always know if it's running

## Files

- `humanamp.service` - systemd service configuration file
- `deploy_service.sh` - Automated deployment script

## Quick Start

### 1. Sync code to Pi
From your Mac, run the sync script (if not already running):
```bash
./sync_amp.sh
```

### 2. Connect to Pi and deploy
```bash
# Connect to Pi
./connect_pi.sh

# Change to project directory (already done by connect script)
cd /home/yotam/AmpSync/Amp3

# Run deployment script
./sync/deploy_service.sh
```

The deployment script will:
1. Copy the service file to `/etc/systemd/system/`
2. Reload systemd daemon
3. Check current service status
4. Optionally enable and start the service

### 3. Verify it's running
```bash
sudo systemctl status humanamp.service
```

Expected output:
```
● humanamp.service - HumanAmplifier Interactive Game System
   Loaded: loaded (/etc/systemd/system/humanamp.service; enabled)
   Active: active (running) since Mon 2024-11-18 20:00:00 GMT; 5s ago
 Main PID: 1234 (python3)
```

## Management Commands

### Service Control
```bash
# Start the service
sudo systemctl start humanamp.service

# Stop the service
sudo systemctl stop humanamp.service

# Restart the service (after code changes)
sudo systemctl restart humanamp.service

# Check service status
sudo systemctl status humanamp.service
```

### Auto-Start Configuration
```bash
# Enable auto-start on boot
sudo systemctl enable humanamp.service

# Disable auto-start (service stays installed but won't start on boot)
sudo systemctl disable humanamp.service
```

### Viewing Logs
```bash
# View live logs (like tail -f)
sudo journalctl -u humanamp.service -f

# View last 100 lines
sudo journalctl -u humanamp.service -n 100

# View logs since last boot
sudo journalctl -u humanamp.service -b

# View logs from specific time
sudo journalctl -u humanamp.service --since "1 hour ago"
sudo journalctl -u humanamp.service --since "2024-11-18 10:00:00"

# View only errors
sudo journalctl -u humanamp.service -p err

# Export logs to file
sudo journalctl -u humanamp.service > amp_logs.txt
```

## Workflow: Development with Service

### Option A: Keep service running (production mode)
```bash
# Make code changes on Mac (sync script auto-syncs)
# ...edit code locally...

# Restart service on Pi to apply changes
ssh yotam@raspberrypi.local "sudo systemctl restart humanamp.service"

# View logs
ssh yotam@raspberrypi.local "sudo journalctl -u humanamp.service -f"
```

### Option B: Manual testing (development mode)
```bash
# Connect to Pi
./connect_pi.sh

# Stop the service temporarily
sudo systemctl stop humanamp.service

# Run manually for testing
run amplifier.py

# When done, restart service
sudo systemctl start humanamp.service
```

## Updating the Service Configuration

If you modify `sync/humanamp.service`:

```bash
# 1. Sync changes to Pi (automatic via sync_amp.sh)

# 2. Connect to Pi
./connect_pi.sh

# 3. Re-run deployment script
./sync/deploy_service.sh
```

The script will automatically restart the service to apply changes.

## Troubleshooting

### Service won't start
```bash
# View detailed error logs
sudo journalctl -u humanamp.service -n 50

# Check if service file is valid
sudo systemctl status humanamp.service

# Test manually first
cd /home/yotam/AmpSync/Amp3
sudo ./venv_pi/bin/python3 src/amplifier.py
```

### Common Issues

**Issue: Python path not found**
```bash
# Verify Python exists
ls -la /home/yotam/AmpSync/Amp3/venv_pi/bin/python3

# Fix: Make sure venv_pi is created and dependencies installed
cd /home/yotam/AmpSync/Amp3
python3 -m venv venv_pi
source venv_pi/bin/activate
pip install -r requirements.txt
```

**Issue: Permission denied on GPIO**
- Service runs as root, so GPIO access should work
- Check that rpi-ws281x is installed: `pip list | grep rpi-ws281x`

**Issue: Audio not working**
- Ensure pygame is installed: `pip list | grep pygame`
- Check audio output device: `aplay -l`

**Issue: Service keeps restarting (crash loop)**
```bash
# View crash logs
sudo journalctl -u humanamp.service -n 100

# Check for Python exceptions
sudo journalctl -u humanamp.service | grep -A 20 "Traceback"

# Temporarily disable auto-restart for debugging
sudo systemctl stop humanamp.service
# Test manually to see actual error
sudo ./venv_pi/bin/python3 src/amplifier.py
```

### Checking System Resources
```bash
# Check if service is using too much memory/CPU
sudo systemctl status humanamp.service

# View detailed process info
top -p $(pgrep -f "amplifier.py")

# View memory usage
sudo journalctl -u humanamp.service | grep "Memory"
```

## Log Files

The system maintains **two types of logs**:

1. **systemd journal logs** (via journalctl)
   - All stdout/stderr from the Python process
   - Service start/stop events
   - System-level errors

2. **Application log files** (via HybridLogger)
   - Located in: `/home/yotam/AmpSync/Amp3/logs/`
   - Format: `HumanAmplifierSystem_YYYY-MM-DD_HH-MM-SS.log`
   - Detailed application-level logging

Both are useful for different purposes!

## Service Configuration Details

The service is configured to:
- Run as **root** (required for GPIO/LED control)
- Working directory: `/home/yotam/AmpSync/Amp3`
- Python interpreter: `/home/yotam/AmpSync/Amp3/venv_pi/bin/python3`
- Auto-restart: **always** with 10-second delay
- Start after: **network.target** and **sound.target**
- Crash protection: Max 5 restarts in 60 seconds
- Graceful shutdown: 30-second timeout with SIGTERM

## Removing the Service

If you want to completely remove the service:

```bash
# Stop the service
sudo systemctl stop humanamp.service

# Disable auto-start
sudo systemctl disable humanamp.service

# Remove service file
sudo rm /etc/systemd/system/humanamp.service

# Reload systemd
sudo systemctl daemon-reload
```

## Additional Resources

- [systemd service documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [journalctl documentation](https://www.freedesktop.org/software/systemd/man/journalctl.html)



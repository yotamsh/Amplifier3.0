#!/bin/bash
#
# Pi Environment Setup Script
# This script sets up the development environment on the Raspberry Pi
# - Changes to project directory
# - Activates virtual environment  
# - Creates 'run' alias for sudo Python execution
# - Starts interactive bash session
#

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Amp3 development environment...${NC}"

# Change to project directory
cd /home/yotam/AmpSync/Amp3 || {
    echo "Error: Could not change to project directory"
    exit 1
}

# Check if venv exists
if [ ! -d "venv_pi" ]; then
    echo "Error: venv_pi directory not found"
    exit 1
fi

# Activate virtual environment
source venv_pi/bin/activate || {
    echo "Error: Could not activate virtual environment"
    exit 1
}

echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo -e "${GREEN}✓ Current directory: $(pwd)${NC}"
#echo -e "${GREEN}✓ Python path: $(which python3)${NC}"
echo -e "${BLUE}✓ 'run' alias created for: sudo ./venv_pi/bin/python3${NC}"
echo ""

# Start interactive bash with custom setup
exec bash --rcfile <(echo '
# Source the virtual environment again to ensure it is active
source venv_pi/bin/activate 2>/dev/null || true

# Load user bashrc if it exists
source ~/.bashrc 2>/dev/null || true

# Create the run alias
alias run="sudo ./venv_pi/bin/python3"

# Show helpful commands
echo ""
echo "=== Amp3 Pi Environment ==="
echo "Available commands:"
echo "  run <script.py>         - Run with sudo (LED control)"
echo "  python3 <script.py>     - Run without sudo"
echo "  exit                    - Disconnect from Pi"
echo "  sudo shutdown -h now    - Shutdown Pi"
echo ""
')

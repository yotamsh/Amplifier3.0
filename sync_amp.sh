#!/bin/bash
#
# Generic Project Sync Script
# 
# This script continuously syncs a local project to a remote server,
# manages virtual environments, and syncs logs back.
#
# To use for different projects, update the configuration variables below.
#

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration - Update these variables for different projects
LOCAL_PROJECT_DIR="/Users/yotamsh/Downloads/personal/pRepos/Amp3/"
REMOTE_PROJECT_DIR="yotam@raspberrypi.local:/home/yotam/AmpSync/Amp3/"
LOCAL_VENV_NAME="venv_mac"
REMOTE_VENV_NAME="venv_pi"
LOGS_FOLDER="logs"
EXCLUDE_FILE=".rsyncignore"

# Dependency update tracking
LAST_REQ_HASH=""

echo -e "${BLUE}Starting continuous sync between local and remote...${NC}"
echo -e "${BLUE}Local Project: $LOCAL_PROJECT_DIR${NC}"
echo -e "${BLUE}Remote Project: $REMOTE_PROJECT_DIR${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}"
echo ""

# Function to handle cleanup on script exit
cleanup() {
    echo -e "\n${RED}Stopping sync...${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main sync loop
while true; do
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Checking local requirements...${NC}"
    
    # Only update local requirements.txt if packages have changed
    if [ -f "${LOCAL_PROJECT_DIR}${LOCAL_VENV_NAME}/bin/pip" ]; then
        source "${LOCAL_PROJECT_DIR}${LOCAL_VENV_NAME}/bin/activate"
        
        # Get current package list and compare with existing requirements.txt
        CURRENT_PACKAGES=$(pip freeze | sort)
        if [ -f "${LOCAL_PROJECT_DIR}requirements.txt" ]; then
            EXISTING_PACKAGES=$(sort "${LOCAL_PROJECT_DIR}requirements.txt")
        else
            EXISTING_PACKAGES=""
        fi
        
        if [ "$CURRENT_PACKAGES" != "$EXISTING_PACKAGES" ]; then
            pip freeze > "${LOCAL_PROJECT_DIR}requirements.txt"
            echo -e "${GREEN}✓ Local requirements.txt updated (packages changed)${NC}"
        else
            echo -e "${GREEN}✓ Local requirements unchanged${NC}"
        fi
    else
        echo -e "${RED}✗ Virtual environment (${LOCAL_VENV_NAME}) not found, skipping requirements update${NC}"
    fi
    
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Syncing to remote...${NC}"
    
    # Sync local project to remote (excluding files in .rsyncignore)
    rsync -avz --exclude-from="$EXCLUDE_FILE" "$LOCAL_PROJECT_DIR" "$REMOTE_PROJECT_DIR"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Local to remote sync completed${NC}"
        
        # Check if requirements.txt has changed to skip unnecessary updates
        if [ -f "${LOCAL_PROJECT_DIR}requirements.txt" ]; then
            # Cross-platform checksum (macOS uses md5, Linux uses md5sum)
            if command -v md5sum >/dev/null 2>&1; then
                CURRENT_REQ_HASH=$(md5sum "${LOCAL_PROJECT_DIR}requirements.txt" 2>/dev/null | cut -d' ' -f1 || echo "")
            elif command -v md5 >/dev/null 2>&1; then
                CURRENT_REQ_HASH=$(md5 -q "${LOCAL_PROJECT_DIR}requirements.txt" 2>/dev/null || echo "")
            else
                CURRENT_REQ_HASH=$(date +%s)  # Fallback to timestamp if no md5 available
            fi
            
            if [ "$CURRENT_REQ_HASH" = "$LAST_REQ_HASH" ] && [ -n "$LAST_REQ_HASH" ]; then
                echo -e "${GREEN}✓ Requirements unchanged, skipping dependency update${NC}"
                SKIP_DEPS=true
            else
                echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Requirements changed, updating remote dependencies...${NC}"
                LAST_REQ_HASH=$CURRENT_REQ_HASH
                SKIP_DEPS=false
            fi
        else
            echo -e "${RED}✗ requirements.txt not found, skipping dependency update${NC}"
            SKIP_DEPS=true
        fi
        
        # Update remote virtual environment from synced requirements.txt
        if [ "$SKIP_DEPS" = false ]; then
            REMOTE_HOST="${REMOTE_PROJECT_DIR%:*}"       # Extract user@host from user@host:/path format
            REMOTE_HOST_PATH="${REMOTE_PROJECT_DIR#*:}"  # Extract path from user@host:/path format
            ssh "$REMOTE_HOST" "cd $REMOTE_HOST_PATH && ([ -d $REMOTE_VENV_NAME ] || python3 -m venv $REMOTE_VENV_NAME) && source $REMOTE_VENV_NAME/bin/activate && pip install -r requirements.txt --upgrade --quiet"
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ Remote dependencies updated${NC}"
            else
                echo -e "${RED}✗ Failed to update remote dependencies${NC}"
            fi
        fi
        
        # Sync logs back from remote project to local
        echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] Syncing logs from remote...${NC}"
        rsync -avz "$REMOTE_PROJECT_DIR/$LOGS_FOLDER" "$LOCAL_PROJECT_DIR"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Remote logs to local sync completed${NC}"
        else
            echo -e "${RED}✗ Failed to sync logs from remote${NC}"
        fi
    else
        echo -e "${RED}✗ Failed to sync to remote${NC}"
    fi
    
    echo ""
    sleep 5
done

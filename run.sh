#!/bin/bash

# Odus — Launcher Script
# Ensures environment is ready and launches the assistant.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🦉 Starting Odus...${NC}"

# 1. Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found.${NC}"
    if [ -f .env.example ]; then
        echo -e "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${RED}Please edit .env and add your GEMINI_API_KEY before running again.${NC}"
        exit 1
    fi
fi

# 2. Check for API Key
if ! grep -q "GEMINI_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo -e "${RED}Error: GEMINI_API_KEY is not set in .env.${NC}"
    echo -e "Get your key at: https://aistudio.google.com/apikey"
    exit 1
fi

# 3. Ensure Virtual Environment
if [ ! -d .venv ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# 4. Sync Dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
.venv/bin/pip install -q -r requirements.txt

# 5. Wayland/X11 specific checks
if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
    echo -e "${BLUE}Detected Wayland session.${NC}"
    
    # Check for ydotoold service
    if ! systemctl --user is-active --quiet ydotoold; then
        echo -e "${YELLOW}Notice: ydotoold service is not active.${NC}"
        echo -e "To automate this, run: ${GREEN}./scripts/setup_daemon.sh${NC}"
        
        # Fallback check for manual process
        if ! pgrep -x "ydotoold" > /dev/null; then
            echo -e "Proceeding, but input features may fail until the daemon is started."
        fi
    fi
    
    # Qt Wayland fixes
    export QT_QPA_PLATFORM=wayland
fi

# 6. Launch Odus
echo -e "${GREEN}All systems go! Launching...${NC}"
export PYTHONPATH=$PYTHONPATH:.
.venv/bin/python3 -m odus.main

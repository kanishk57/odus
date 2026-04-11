#!/bin/bash

# Odus — Daemon Automation Setup
# Configures ydotoold to run automatically in the background without sudo.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛡️ Setting up ydotoold automation...${NC}"

# 1. Create udev rule for /dev/uinput permissions
# This allows members of the 'input' group to use ydotool without sudo.
echo -e "${BLUE}Creating udev rule for /dev/uinput...${NC}"
cat <<EOF | sudo tee /etc/udev/rules.d/80-odus-uinput.rules > /dev/null
KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
EOF

# 2. Reload udev rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# 3. Create systemd user service directory if it doesn't exist
mkdir -p "$HOME/.config/systemd/user/"

# 4. Create the systemd service file
# Note: $(id -u) and $(id -g) are evaluated now to hardcode the user IDs.
# Or better, we use systemd's %U and %G.
echo -e "${BLUE}Creating systemd user service...${NC}"
cat <<EOF > "$HOME/.config/systemd/user/ydotoold.service"
[Unit]
Description=ydotool daemon for Odus
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/ydotoold --socket-path /tmp/ydotoolsok --socket-own %U:%G
Restart=always

[Install]
WantedBy=default.target
EOF

# 5. Reload systemd and start the service
echo -e "${BLUE}Starting ydotoold service...${NC}"
systemctl --user daemon-reload
systemctl --user enable ydotoold.service
systemctl --user restart ydotoold.service

echo -e "\n${GREEN}✅ Success! ydotoold is now running in the background as a user service.${NC}"
echo -e "It will start automatically every time you log in."
echo -e "Check status with: ${BLUE}systemctl --user status ydotoold${NC}"

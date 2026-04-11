#!/bin/bash

# Odus — System Tools Setup Script
# Installs required backends for screen capture and input simulation.

set -e

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🦉 Odus System Setup — Identifying Distribution...${NC}"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_LIKE=$ID_LIKE
else
    echo -e "${RED}Error: Cannot detect OS distribution. Please install requirements manually.${NC}"
    exit 1
fi

echo -e "Detected: ${GREEN}$PRETTY_NAME${NC}"

case "$OS" in
    ubuntu|debian|pop|mint)
        echo -e "${BLUE}Installing dependencies for Debian-based system (apt)...${NC}"
        sudo apt update
        sudo apt install -y \
            ydotool ydotoold \
            grim slurp \
            xdotool \
            gnome-screenshot \
            gstreamer1.0-tools \
            gstreamer1.0-plugins-good \
            libnotify-bin
        ;;
    fedora)
        echo -e "${BLUE}Installing dependencies for Fedora (dnf)...${NC}"
        sudo dnf install -y \
            ydotool \
            grim slurp \
            xdotool \
            gnome-screenshot \
            gstreamer1-plugins-good \
            libnotify
        ;;
    arch)
        echo -e "${BLUE}Installing dependencies for Arch (pacman)...${NC}"
        sudo pacman -S --needed --noconfirm \
            ydotool \
            grim slurp \
            xdotool \
            gnome-screenshot \
            gst-plugins-good \
            libnotify
        ;;
    *)
        if [[ "$OS_LIKE" == *"debian"* ]]; then
            echo -e "${BLUE}Installing dependencies for Debian-like system (apt)...${NC}"
            sudo apt update
            sudo apt install -y ydotool ydotoold grim slurp xdotool gnome-screenshot gstreamer1.0-tools libnotify-bin
        else
            echo -e "${RED}Unsupported distribution: $OS. Please install ydotool and grim manually.${NC}"
            exit 1
        fi
        ;;
esac

echo -e "\n${GREEN}✅ System dependencies installed successfully!${NC}"
echo -e "${BLUE}Note: To use ydotool on Wayland, you may need to start ydotoold:${NC}"
echo -e "sudo ydotoold --socket-path /tmp/ydotoolsok --socket-own \$(id -u):\$(id -g)"

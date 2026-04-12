#!/bin/bash
set -e

# Odus Deployment Script
# Targets: GNOME 45+ (Wayland)

PROJECT_ROOT=$(pwd)
EXTENSION_DIR="$PROJECT_ROOT/gnome-extension"
UUID="odus-bridge@visionnestllc.com"
INSTALL_PATH="$HOME/.local/share/gnome-shell/extensions/$UUID"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "------------------------------------------------"
echo "🚀 Starting Odus Deployment..."
echo "------------------------------------------------"

# 1. GNOME Extension Installation
echo "[Extension] Compiling GSettings schemas..."
glib-compile-schemas "$EXTENSION_DIR/schemas/"

echo "[Extension] Installing to $INSTALL_PATH..."
mkdir -p "$HOME/.local/share/gnome-shell/extensions/"
gnome-extensions disable "$UUID" >/dev/null 2>&1 || true
rm -rf "$INSTALL_PATH"
cp -r "$EXTENSION_DIR" "$INSTALL_PATH"
glib-compile-schemas "$INSTALL_PATH/schemas/"

echo "[Extension] Enabling $UUID..."
gnome-extensions enable "$UUID" || echo "⚠️  Could not enable extension automatically. Please restart GNOME Shell and enable it manually."

# 2. Python Environment Setup
echo "[Python] Setting up virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

echo "[Python] Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

# 3. Systemd User Service Configuration
SERVICE_PATH="$HOME/.config/systemd/user/odus.service"
echo "[Systemd] Creating user service at $SERVICE_PATH..."
mkdir -p "$HOME/.config/systemd/user/"

cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=Odus AI Mentor Background Service
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=$VENV_DIR/bin/python3 odus/main_v2_gnome.py
Restart=always
Environment=PYTHONPATH=$PROJECT_ROOT
Environment=XDG_RUNTIME_DIR=/run/user/%U
EnvironmentFile=$PROJECT_ROOT/.env

[Install]
WantedBy=default.target
EOF

echo "[Systemd] Reloading and starting service..."
systemctl --user daemon-reload
systemctl --user enable odus.service
systemctl --user restart odus.service

echo "------------------------------------------------"
echo "✅ Deployment Complete!"
echo "------------------------------------------------"
echo "Next steps:"
echo "1. If this is a Wayland session, you MUST log out and log back in for the GNOME Extension to load."
echo "2. Ensure GEMINI_API_KEY is set in your .env file."
echo "3. Check logs with: journalctl --user -u odus -f"
echo "------------------------------------------------"

# Odus GNOME Bridge Extension

This extension provides a secure D-Bus bridge between the GNOME Shell (Mutter) and the Odus Python backend.

## Features
- **Zero-Privilege Input**: Injects keystrokes directly into the compositor using `Clutter.VirtualInputDevice`.
- **Mutual Authentication**: Hardened D-Bus access using a token-based handshake.
- **Wayland Native**: Works in Wayland environments where traditional tools like `xdotool` fail.
- **Advice Modals**: System-level overlays that display AI-generated fixes and capture user approval.
- **Interactive Follow-ups**: Submit queries directly from the Shell UI back to the Odus brain.

## Installation

The recommended way to install and configure the extension is using the automated deployment script in the project root. This script handles dependency checks, schema compilation, and setting up the background service.

```bash
# In the project root
./deploy.sh
```

### Steps Performed by Deploy Script:
1. **Dependency Sync**: Checks for Python 3.11+, `dbus-next`, and GNOME Shell development headers.
2. **Schema Compilation**: Automatically compiles the XML settings schemas.
3. **Extension Install**: Links the extension to `~/.local/share/gnome-shell/extensions/`.
4. **Daemon Setup**: Configures and starts a `systemctl --user` service for the Odus background logic.

## Post-Installation
1. **Enable Extension**: Use the **Extensions** app or run:
   ```bash
   gnome-extensions enable odus-bridge@visionnestllc.com
   ```
2. **Restart Shell**: If on Wayland, you **must log out and log back in** for the extension to be recognized by the compositor.
3. **Check Status**:
   - Extension state: `gnome-extensions show odus-bridge@visionnestllc.com`
   - Daemon logs: `journalctl --user -u odus -f`

## Development
- **D-Bus Interface**: `org.gnome.Odus`
- **Object Path**: `/org/gnome/Odus`
- **Auth Token**: Stored in `$XDG_RUNTIME_DIR/odus_token` (0600 permissions).

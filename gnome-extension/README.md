# Odus GNOME Bridge Extension

This extension provides a secure D-Bus bridge between the GNOME Shell (Mutter) and the Odus Python backend.

## Features
- **Zero-Privilege Input**: Injects keystrokes directly into the compositor using `Clutter.VirtualInputDevice`.
- **Mutual Authentication**: Hardened D-Bus access using a token-based handshake.
- **Wayland Native**: Works in Wayland environments where traditional tools like `xdotool` fail.

## Installation
1. Copy this directory to the local extensions path:
   ```bash
   mkdir -p ~/.local/share/gnome-shell/extensions/
   cp -r gnome-extension ~/.local/share/gnome-shell/extensions/odus-bridge@visionnestllc.com
   ```
2. Restart GNOME Shell:
   - **X11**: `Alt+F2`, then type `r` and press Enter.
   - **Wayland**: Log out and log back in.
3. Enable the extension:
   ```bash
   gnome-extensions enable odus-bridge@visionnestllc.com
   ```

## Development
- **D-Bus Interface**: `org.gnome.Odus`
- **Object Path**: `/org/gnome/Odus`
- **Auth Token**: Stored in `$XDG_RUNTIME_DIR/odus_token` (0600 permissions).

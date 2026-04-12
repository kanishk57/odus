# Extension Status and Troubleshooting: Odus Bridge

## Current State
- **Installation Path:** `~/.local/share/gnome-shell/extensions/odus-bridge@visionnestllc.com/`
- **Metadata:** Verified as correctly structured with `uuid`, `shell-version` (covering 46, 47, 48), and `settings-schema`.
- **Status:** Not currently appearing in `gnome-extensions list`.

## Troubleshooting Performed
- Verified file permissions and path structure: Confirmed files are present and readable by the user `armaan`.
- Validated `metadata.json`: Checked for syntax, valid fields, and proper schema declarations.
- Syncing: Performed clean re-copies of the extension directory to ensure no stale artifacts.
- Wayland Consideration: Acknowledged the extension environment on Wayland, which often requires a full GNOME Shell process refresh to detect new extension directories.

## Required Actions for Detection
1. **Force GNOME Shell Refresh:**
   - Press `Alt+F2` on your keyboard.
   - Type `r` and press `Enter`. 
   *Note: This restarts the shell process and will force a re-scan of the `~/.local/share/gnome-shell/extensions/` directory.*

2. **Verify Installation:**
   - Run the following command in your terminal after the shell refresh:
     ```bash
     gnome-extensions list | grep odus
     ```

3. **Check for Errors:**
   - If the extension still does not appear, check the system journal for specific loading errors:
     ```bash
     journalctl /usr/bin/gnome-shell --since "5 minutes ago" | grep -i odus
     ```

## Summary for User
The extension files are correctly placed. The issue is that the GNOME Shell has not yet indexed the new folder. A shell refresh (Alt+F2 -> 'r') is the standard way to resolve this detection issue on Wayland.

## Next Steps
1. Run deployment:
   ```bash
   ./deploy.sh
   ```

2. Log out and log back in to GNOME if you are on Wayland.

3. Enable and inspect the extension if needed:
   ```bash
   gnome-extensions enable odus-bridge@visionnestllc.com
   gnome-extensions info odus-bridge@visionnestllc.com
   ```

4. Watch GNOME Shell logs for extension load errors:
   ```bash
   journalctl /usr/bin/gnome-shell -f
   ```

5. Verify the token was created:
   ```bash
   ls "$XDG_RUNTIME_DIR/odus"
   ```

6. If it fails, collect log lines mentioning `OdusBridge` or `odus-bridge@visionnestllc.com`.

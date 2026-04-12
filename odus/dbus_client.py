import os
import asyncio
import mmap
import json
from dbus_next.aio import MessageBus
from dbus_next import Message, MessageType

class OdusDBusClient:
    def __init__(self):
        self.bus = None
        self.interface = None
        self.token = self._load_token()
        self.authenticated = False

    def _load_token(self):
        runtime_dir = os.environ.get('XDG_RUNTIME_DIR', f"/run/user/{os.getuid()}")
        token_path = os.path.join(runtime_dir, 'odus', 'token')
        
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Odus token not found at {token_path}. Is the GNOME extension enabled?")
            
        with open(token_path, 'r') as f:
            return f.read().strip()

    async def connect(self):
        """Connects to the session bus and authenticates with the GNOME extension."""
        try:
            self.bus = await MessageBus(negotiate_unix_fd=True).connect()
            
            # Introspect the Odus service
            introspection = await self.bus.introspect('org.gnome.Odus', '/org/gnome/Odus')
            proxy_object = self.bus.get_proxy_object('org.gnome.Odus', '/org/gnome/Odus', introspection)
            self.interface = proxy_object.get_interface('org.gnome.Odus')

            # Perform handshake
            success = await self.interface.call_register_client(self.token)
            if success:
                print("[OdusClient] Successfully authenticated with GNOME extension.")
                self.authenticated = True
            else:
                print("[OdusClient] Authentication failed. Token mismatch.")
                self.authenticated = False
                
        except Exception as e:
            print(f"[OdusClient] Failed to connect to D-Bus: {e}")
            raise

    async def capture_screen(self) -> bytes:
        """Captures a screenshot via the GNOME extension and returns raw bytes (PNG)."""
        if not self.authenticated:
            return b""

        try:
            # dbus-next returns the FD in a way that can be accessed
            # We need to use call() to handle Unix FDs properly sometimes, 
            # but high-level proxy often handles it.
            fd = await self.interface.call_capture_screen()
            
            # Map the FD and read
            with os.fdopen(fd, 'rb') as f:
                # Seek to end to get size
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(0)
                
                if size == 0:
                    return b""
                
                # Use mmap for zero-copy read
                with mmap.mmap(f.fileno(), size, access=mmap.ACCESS_READ) as mm:
                    return mm.read()
                    
        except Exception as e:
            print(f"[OdusClient] CaptureScreen failed: {e}")
            return b""

    async def inject_keystroke(self, keysym: str):
        """Injects a keystroke via the GNOME extension."""
        if not self.authenticated:
            print("[OdusClient] Error: Not authenticated.")
            return

        try:
            await self.interface.call_inject_keystroke(keysym)
        except Exception as e:
            print(f"[OdusClient] Failed to inject keystroke '{keysym}': {e}")

    async def set_mascot_state(self, state: str):
        """Updates the mascot state in the GNOME extension."""
        if not self.authenticated:
            return

        try:
            await self.interface.call_set_mascot_state(state)
        except Exception as e:
            print(f"[OdusClient] Failed to set mascot state: {e}")

    async def request_approval(self, summary: str, explanation: str, follow_up: str, command: str, kind: str = "advice", retry_after: float | None = None) -> bool:
        """Requests user approval and shows advice in a GNOME Shell modal."""
        if not self.authenticated:
            return False

        try:
            payload = json.dumps({
                "summary": summary,
                "explanation": explanation,
                "follow_up": follow_up,
                "command": command,
                "kind": kind,
                "retry_after": retry_after,
            })
            return await self.interface.call_request_action_approval(payload)
        except Exception as e:
            print(f"[OdusClient] Approval request failed: {e}")
            return False

    def on_hotkey_triggered(self, callback):
        """Registers a callback for the HotkeyTriggered D-Bus signal."""
        if not self.interface:
            raise RuntimeError("Not connected to D-Bus")

        self.interface.on_hotkey_triggered(callback)

async def main():
    # Example usage
    client = OdusDBusClient()
    await client.connect()
    
    if client.authenticated:
        print("Injecting 'Return' key in 2 seconds...")
        await asyncio.sleep(2)
        await client.inject_keystroke("Return")
        
        print("Changing mascot to 'thinking'...")
        await client.set_mascot_state("thinking")

if __name__ == "__main__":
    asyncio.run(main())

"""
Odus (v2) — Main Entry Point for Sidebar UI.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
import signal

os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"
os.environ["GTK_THEME"] = "Adwaita:dark"

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("odus")

from PyQt6.QtWidgets import QApplication
import qasync

async def app_main() -> None:
    """Sets up all subsystems with v2 Sidebar/Window UI."""

    # 1. Initialize UI (v2)
    from odus.ui_v2.app import OdusAppV2
    ui_type = os.getenv("ODUS_UI_TYPE", "window") # Default to window now as fallback
    odus_app = OdusAppV2(ui_type=ui_type)
    odus_app.start()

    # 2. Start the agentic loop
    from odus.reasoning.agent import Agent
    agent = Agent()
    asyncio.create_task(agent.start())

    # 3. Start the hotkey listener
    from odus.perception.hotkey import HotkeyListener
    hotkey = HotkeyListener()
    hotkey.start()

    logger.info("🦉 Odus v2 Sidebar is ready! Press Ctrl+Shift+O to capture your screen.")

def main() -> None:
    """CLI entry point."""
    app = QApplication(sys.argv)
    
    def handle_sigterm(*args):
        logger.info("Received SIGTERM, shutting down...")
        QApplication.quit()
    
    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        with loop:
            loop.run_until_complete(app_main())
            loop.run_forever()

    except KeyboardInterrupt:
        logger.info("Odus shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()

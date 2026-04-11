"""
Odus — Main Entry Point.

Wires together all layers:
  Perception (hotkey + capture) → Reasoning (Gemini Vision + agent) →
  Action (executor + safety + PTY + input sim) → UI (unified window)

Usage:
    python -m odus.main
"""

from __future__ import annotations

import asyncio
import logging
import sys

from dotenv import load_dotenv

# Load .env before anything else
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("odus")


from PyQt6.QtWidgets import QApplication
import qasync


async def app_main() -> None:
    """PyQt6 async entry point — sets up all subsystems."""

    # 1. Initialize UI (creates unified window)
    from odus.ui.app import OdusApp
    odus_app = OdusApp()
    odus_app.start()

    # 2. Start the agentic loop (runs in background)
    from odus.reasoning.agent import Agent
    agent = Agent()
    asyncio.create_task(agent.start())

    # 3. Start the hotkey listener (background thread)
    from odus.perception.hotkey import HotkeyListener
    hotkey = HotkeyListener()
    hotkey.start()

    logger.info("🦉 Odus is ready! Press Ctrl+Shift+O to capture your screen.")


def main() -> None:
    """CLI entry point."""
    try:
        app = QApplication(sys.argv)
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

"""
Odus Event Bus — Cross-layer communication system.

This is the ONLY communication channel between Perception, Reasoning,
Action, and UI layers. No module should import another layer's internals.
All cross-layer communication flows through OdusEvent objects.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(Enum):
    """All possible event types in the Odus pipeline."""

    # Perception events
    CAPTURE_STARTED = "capture_started"
    CAPTURE_DONE = "capture_done"

    # Reasoning events
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_DONE = "analysis_done"
    ANALYSIS_STREAMING = "analysis_streaming"  # Partial token for Ghost Terminal

    # Action events
    CONFIRM_REQUIRED = "confirm_required"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_DONE = "execution_done"

    # User interaction events
    USER_CONFIRMED = "user_confirmed"
    USER_DENIED = "user_denied"

    # Input action events (agentic desktop control)
    INPUT_ACTION_PLANNED = "input_action_planned"       # Agent wants to perform a GUI action
    INPUT_ACTION_CONFIRMED = "input_action_confirmed"   # User approved the GUI action
    INPUT_ACTION_EXECUTING = "input_action_executing"   # GUI action in progress
    INPUT_ACTION_DONE = "input_action_done"             # GUI action completed
    INPUT_ACTION_FAILED = "input_action_failed"         # GUI action failed

    # Multi-step agent plan events
    AGENT_PLAN_CREATED = "agent_plan_created"           # Agent produced a multi-step plan
    AGENT_STEP_STARTED = "agent_step_started"           # Starting a plan step
    AGENT_STEP_DONE = "agent_step_done"                 # Step completed successfully
    AGENT_PLAN_DONE = "agent_plan_done"                 # All plan steps finished

    # Permission events (file/repo access)
    PERMISSION_REQUESTED = "permission_requested"       # Agent requests access to a resource
    PERMISSION_GRANTED = "permission_granted"           # User clicked "Allow"
    PERMISSION_DENIED = "permission_denied"             # User clicked "Deny"

    # Terminal streaming events (PTY)
    TERMINAL_OUTPUT_LINE = "terminal_output_line"       # PTY streamed a line of output
    TERMINAL_COMMAND_STARTED = "terminal_command_started"  # PTY command began
    TERMINAL_COMMAND_DONE = "terminal_command_done"     # PTY command finished
    TERMINAL_CWD_CHANGED = "terminal_cwd_changed"       # Working directory changed

    # UI events
    TAB_SWITCH = "tab_switch"                           # Switch between chat/terminal tabs

    # System events
    ERROR = "error"
    STATUS_UPDATE = "status_update"


@dataclass
class OdusEvent:
    """A single event flowing through the event bus."""

    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """
    Async event bus supporting multiple listeners.

    Usage:
        bus = get_event_bus()

        # Producer
        await bus.emit(OdusEvent(EventType.CAPTURE_DONE, {"image": bytes_data}))

        # Consumer
        async for event in bus.listen():
            if event.type == EventType.CAPTURE_DONE:
                handle_capture(event.payload)
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[OdusEvent]] = []

    async def emit(self, event: OdusEvent) -> None:
        """Broadcast an event to ALL listeners."""
        for queue in self._subscribers:
            await queue.put(event)

    def listen(self) -> _EventListener:
        """Create a new listener. Returns an async iterator of events."""
        queue: asyncio.Queue[OdusEvent] = asyncio.Queue()
        self._subscribers.append(queue)
        return _EventListener(queue, self._subscribers)


class _EventListener:
    """Async iterator that yields events from the bus."""

    def __init__(
        self,
        queue: asyncio.Queue[OdusEvent],
        subscribers: list[asyncio.Queue[OdusEvent]],
    ) -> None:
        self._queue = queue
        self._subscribers = subscribers

    def __aiter__(self):
        return self

    async def __anext__(self) -> OdusEvent:
        return await self._queue.get()

    def unsubscribe(self) -> None:
        """Remove this listener from the bus."""
        if self._queue in self._subscribers:
            self._subscribers.remove(self._queue)


# ── Singleton ──────────────────────────────────────────────────────────
_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the global singleton event bus."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance

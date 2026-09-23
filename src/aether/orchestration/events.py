from typing import Callable, Dict, List, Any, Type
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger("aether.orchestration.events")

@dataclass
class Event:
    """Base class for all system events."""
    type: str
    payload: Dict[str, Any]

class EventBus:
    """
    Asynchronous event bus for internal system communication.
    Facilitates decoupled component interaction via state change notifications.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Register a callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}: {callback.__name__}")

    async def publish(self, event: Event):
        """Publish an event to all registered subscribers."""
        if event.type not in self._subscribers:
            return

        logger.debug(f"Publishing event {event.type}: {event.payload}")
        # Use gather directly on the callbacks to ensure they run in the current loop
        # rather than creating background tasks that might not finish before the test asserts.
        await asyncio.gather(
            *[callback(event) for callback in self._subscribers[event.type]],
            return_exceptions=True
        )

# Global event bus instance
bus = EventBus()

"""Event management system for handling asynchronous events"""
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Event:
    """Event data structure"""
    type: str
    data: Any
    timestamp: Optional[str] = None
    source: Optional[str] = None

class EventManager:
    """Manages event subscriptions and dispatching"""
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._immediate_mode = False
        self._pending_tasks: Set[asyncio.Task] = set()
        self._timeout = 10.0  # Default timeout in seconds
        self.logger = logging.getLogger(__name__)

    @property
    def immediate_mode(self) -> bool:
        """Get immediate mode status"""
        return self._immediate_mode

    @immediate_mode.setter
    def immediate_mode(self, value: bool):
        """Set immediate mode status"""
        self._immediate_mode = value

    @property
    def timeout(self) -> float:
        """Get handler timeout"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float):
        """Set handler timeout"""
        self._timeout = value

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def on(self, event_type: str, handler: Callable) -> None:
        """Alias for subscribe"""
        self.subscribe(event_type, handler)

    def off(self, event_type: str, handler: Callable) -> None:
        """Alias for unsubscribe"""
        self.unsubscribe(event_type, handler)

    def remove_listener(self, event_type: str, handler: Callable) -> None:
        """Alias for unsubscribe"""
        self.unsubscribe(event_type, handler)

    async def _handle_event(self, handler: Callable, event: Event) -> None:
        """Handle a single event with timeout"""
        try:
            await asyncio.wait_for(handler(event), timeout=self._timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"Handler for {event.type} timed out after {self._timeout}s")
        except Exception as e:
            self.logger.error(f"Error in event handler for {event.type}: {e}")

    async def emit(self, event_type: str, data: Any) -> None:
        """Emit an event to all subscribers"""
        if event_type not in self._handlers:
            return

        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.now().isoformat(),
            source="event_manager"
        )
        
        handlers = self._handlers[event_type].copy()
        tasks = []

        for handler in handlers:
            if self._immediate_mode:
                await self._handle_event(handler, event)
            else:
                task = asyncio.create_task(self._handle_event(handler, event))
                tasks.append(task)
                self._pending_tasks.add(task)
                task.add_done_callback(self._pending_tasks.discard)

        if not self._immediate_mode and tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def wait_for_handlers(self, timeout: Optional[float] = None) -> None:
        """Wait for all pending event handlers to complete"""
        if not self._pending_tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._pending_tasks, return_exceptions=True),
                timeout=timeout or self._timeout
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Waiting for handlers timed out after {timeout or self._timeout}s")
            # Cancel remaining tasks
            for task in self._pending_tasks:
                if not task.done():
                    task.cancel()
            # Wait for cancellation to complete
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)

    def clear_handlers(self) -> None:
        """Clear all event handlers and cancel pending tasks"""
        # Cancel all pending tasks
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()
        self._handlers.clear()

# Global event manager instance
event_manager = EventManager()

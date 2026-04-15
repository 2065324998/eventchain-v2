"""Projection building from event streams."""

from typing import Any, Callable, Optional

from eventchain.event import Event
from eventchain.store import EventStore


class Projection:
    """Builds read-model projections from event streams.

    Projections subscribe to specific event types and maintain a derived
    view of the data optimized for queries.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._state: dict[str, Any] = {}
        self._processed_count: int = 0

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._state)

    @property
    def processed_count(self) -> int:
        return self._processed_count

    def when(self, event_type: str, handler: Callable[[Event, dict], None]):
        """Register a handler for an event type.

        The handler receives the event and the current projection state dict.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        return self

    def process(self, event: Event) -> None:
        """Process a single event through registered handlers."""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            handler(event, self._state)
        self._processed_count += 1

    def process_all(self, events: list[Event]) -> None:
        """Process a list of events in order."""
        for event in events:
            self.process(event)

    def build_from_store(self, store: EventStore,
                         aggregate_id: str) -> dict[str, Any]:
        """Build the projection from all events in a stream."""
        events = store.get_all_events(aggregate_id)
        self.process_all(events)
        return self.state

    def reset(self) -> None:
        """Reset the projection state."""
        self._state.clear()
        self._processed_count = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the projection state."""
        return self._state.get(key, default)

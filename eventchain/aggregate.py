"""Aggregate root base class for domain objects."""

from copy import deepcopy
from typing import Any, Optional

from eventchain.event import Event
from eventchain.store import EventStore


class AggregateRoot:
    """Base class for aggregate roots in the domain model.

    Subclasses define apply_<event_type> methods that handle each event type.
    The aggregate tracks its current version and can be rebuilt from events.
    """

    def __init__(self):
        self._version: int = 0
        self._aggregate_id: Optional[str] = None
        self._pending_events: list[Event] = []

    @property
    def version(self) -> int:
        return self._version

    @property
    def aggregate_id(self) -> Optional[str]:
        return self._aggregate_id

    def create(self, store: EventStore, aggregate_id: str,
               data: dict[str, Any], event_class: type) -> Event:
        """Create a new aggregate by appending the first event."""
        self._aggregate_id = aggregate_id
        event_type = event_class.__name__
        event = store.append(aggregate_id, event_type, data)
        self._apply(event)
        return event

    def apply_event(self, store: EventStore, aggregate_id: str,
                    data: dict[str, Any], event_class: type,
                    metadata: Optional[dict] = None) -> Event:
        """Apply a new event to the aggregate."""
        if self._aggregate_id is None:
            self._aggregate_id = aggregate_id

        event_type = event_class.__name__
        event = store.append(aggregate_id, event_type, data, metadata)
        self._apply(event)
        return event

    def _apply(self, event: Event) -> None:
        """Route an event to the appropriate handler method."""
        handler_name = f"apply_{self._to_snake_case(event.event_type)}"
        handler = getattr(self, handler_name, None)
        if handler is not None:
            handler(event)
        self._version = event.version

    def load_from_events(self, events: list[Event]) -> None:
        """Rebuild aggregate state from a sequence of events."""
        for event in events:
            self._apply(event)

    def load_from_snapshot(self, snapshot_data: dict[str, Any],
                          version: int) -> None:
        """Restore aggregate state from a snapshot."""
        self._version = version
        self._restore_from_snapshot(snapshot_data)

    def _restore_from_snapshot(self, data: dict[str, Any]) -> None:
        """Override in subclasses to restore state from snapshot data.

        The default implementation sets attributes from the snapshot dict.
        This works for simple value types. Subclasses with complex state
        should override this for proper deep restoration.
        """
        for key, value in data.items():
            if not key.startswith("_"):
                setattr(self, key, value)

    def take_snapshot(self) -> dict[str, Any]:
        """Capture the current state as a snapshot.

        Returns a dictionary of all public (non-underscore) attributes.
        This captures the aggregate's domain state for later restoration.
        """
        state = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                state[key] = deepcopy(value)
        return state

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result.append("_")
            result.append(char.lower())
        return "".join(result)

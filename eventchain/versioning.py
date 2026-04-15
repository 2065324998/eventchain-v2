"""Event versioning and upcasting support."""

from typing import Any, Callable, Optional
from copy import deepcopy

from eventchain.event import Event


class EventUpcaster:
    """Transforms events from older schema versions to newer ones.

    When event schemas evolve, upcasters allow old events stored in the
    event store to be transparently upgraded when replayed.
    """

    def __init__(self):
        self._upcasters: dict[str, list[Callable]] = {}

    def register(self, event_type: str,
                 from_version: int, to_version: int,
                 transform: Callable[[dict], dict]) -> "EventUpcaster":
        """Register an upcaster for an event type.

        The transform function receives the event data dict and returns
        the transformed data dict for the next version.
        """
        key = f"{event_type}:{from_version}:{to_version}"
        if event_type not in self._upcasters:
            self._upcasters[event_type] = []
        self._upcasters[event_type].append({
            "from_version": from_version,
            "to_version": to_version,
            "transform": transform,
        })
        # Sort by from_version for sequential application
        self._upcasters[event_type].sort(key=lambda u: u["from_version"])
        return self

    def upcast(self, event: Event, schema_version: int = 1) -> Event:
        """Upcast an event to the latest schema version.

        Applies all registered upcasters sequentially from the event's
        current schema version to the latest version.
        """
        upcasters = self._upcasters.get(event.event_type, [])
        if not upcasters:
            return event

        data = deepcopy(event.data)
        current_version = event.metadata.get("schema_version", schema_version)

        for upcaster in upcasters:
            if upcaster["from_version"] == current_version:
                data = upcaster["transform"](data)
                current_version = upcaster["to_version"]

        return Event(
            event_id=event.event_id,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            data=data,
            version=event.version,
            timestamp=event.timestamp,
            metadata={**event.metadata, "schema_version": current_version},
        )

    def upcast_stream(self, events: list[Event]) -> list[Event]:
        """Upcast a list of events."""
        return [self.upcast(event) for event in events]

"""In-memory event store implementation."""

from typing import Optional
from collections import defaultdict

from eventchain.event import Event


class EventStore:
    """Append-only event store backed by an in-memory dictionary.

    Events are stored per aggregate ID and assigned monotonically increasing
    version numbers within each aggregate stream. Supports querying events
    by aggregate ID and optional version filtering.
    """

    def __init__(self):
        self._streams: dict[str, list[Event]] = defaultdict(list)
        self._global_position: int = 0

    def append(self, aggregate_id: str, event_type: str, data: dict,
               metadata: Optional[dict] = None) -> Event:
        """Append a new event to an aggregate's stream.

        The event is assigned the next version number in the stream and
        a global position for cross-stream ordering.
        """
        stream = self._streams[aggregate_id]
        version = len(stream) + 1

        event = Event(
            aggregate_id=aggregate_id,
            event_type=event_type,
            data=data,
            version=version,
            metadata=metadata or {},
        )

        stream.append(event)
        self._global_position += 1
        return event

    def get_events(self, aggregate_id: str,
                   min_version: int = 0) -> list[Event]:
        """Get events for an aggregate starting from a minimum version.

        Returns events with version >= min_version (inclusive). When
        min_version is 0 (the default), all events are returned since
        event versions start at 1.

        This is primarily used for partial replay scenarios where only
        events from a certain point onward are needed.
        """
        stream = self._streams.get(aggregate_id, [])
        return [e for e in stream if e.version >= min_version]

    def get_all_events(self, aggregate_id: str) -> list[Event]:
        """Get all events for an aggregate in version order."""
        return list(self._streams.get(aggregate_id, []))

    def get_latest_version(self, aggregate_id: str) -> int:
        """Get the latest version number for an aggregate."""
        stream = self._streams.get(aggregate_id, [])
        if not stream:
            return 0
        return stream[-1].version

    def stream_exists(self, aggregate_id: str) -> bool:
        """Check if an event stream exists for the given aggregate."""
        return aggregate_id in self._streams and len(self._streams[aggregate_id]) > 0

    def get_event_count(self, aggregate_id: str) -> int:
        """Get the number of events in an aggregate's stream."""
        return len(self._streams.get(aggregate_id, []))

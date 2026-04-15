"""Event replay engine for rebuilding aggregate state."""

from typing import Optional, Type

from eventchain.event import Event
from eventchain.store import EventStore
from eventchain.aggregate import AggregateRoot
from eventchain.snapshot import SnapshotStore


class ReplayEngine:
    """Replays events to rebuild aggregate state.

    Supports full replay from the beginning of the stream, or partial
    replay from a snapshot. When a snapshot store is provided, the engine
    automatically uses the latest snapshot as a starting point and only
    replays events that occurred after the snapshot.
    """

    def __init__(self, event_store: EventStore,
                 snapshot_store: Optional[SnapshotStore] = None):
        self._event_store = event_store
        self._snapshot_store = snapshot_store

    def rebuild(self, aggregate_id: str,
                aggregate_class: Type[AggregateRoot]) -> AggregateRoot:
        """Rebuild an aggregate from its event stream.

        If a snapshot store is configured and contains a snapshot for
        this aggregate, the engine restores from the snapshot and only
        replays subsequent events. Otherwise, it replays all events.
        """
        aggregate = aggregate_class()
        aggregate._aggregate_id = aggregate_id

        if self._snapshot_store is not None:
            snapshot = self._snapshot_store.get_latest(aggregate_id)
            if snapshot is not None:
                aggregate.load_from_snapshot(snapshot.data, snapshot.version)
                # Replay events after the snapshot version
                events = self._event_store.get_events(
                    aggregate_id,
                    min_version=snapshot.version + 1
                )
                aggregate.load_from_events(events)
                return aggregate

        # No snapshot available — full replay
        events = self._event_store.get_all_events(aggregate_id)
        aggregate.load_from_events(events)
        return aggregate

    def replay_to_version(self, aggregate_id: str,
                          aggregate_class: Type[AggregateRoot],
                          target_version: int) -> AggregateRoot:
        """Rebuild an aggregate up to a specific version."""
        aggregate = aggregate_class()
        aggregate._aggregate_id = aggregate_id

        events = self._event_store.get_all_events(aggregate_id)
        filtered = [e for e in events if e.version <= target_version]
        aggregate.load_from_events(filtered)
        return aggregate

    def take_snapshot(self, aggregate_id: str,
                      aggregate_class: Type[AggregateRoot]) -> None:
        """Rebuild an aggregate and save a snapshot of its current state."""
        if self._snapshot_store is None:
            raise RuntimeError("No snapshot store configured")

        aggregate = self.rebuild(aggregate_id, aggregate_class)
        snapshot_data = aggregate.take_snapshot()
        self._snapshot_store.save(
            aggregate_id, aggregate.version, snapshot_data
        )

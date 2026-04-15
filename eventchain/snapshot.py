"""Snapshot store for fast aggregate restoration."""

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Snapshot:
    """A point-in-time capture of an aggregate's state."""
    aggregate_id: str
    version: int
    data: dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SnapshotStore:
    """Stores snapshots for fast aggregate restoration.

    When restoring an aggregate, the snapshot provides the state at a known
    version, and only events starting from version (snapshot.version + 1)
    need to be replayed. This dramatically speeds up loading for aggregates
    with many events.
    """

    def __init__(self):
        self._snapshots: dict[str, list[Snapshot]] = {}

    def save(self, aggregate_id: str, version: int,
             data: dict[str, Any]) -> Snapshot:
        """Save a snapshot of an aggregate at a given version.

        The version parameter indicates the event version that this snapshot
        represents. When used for replay, events with version > snapshot.version
        are replayed on top of the restored state.
        """
        snapshot = Snapshot(
            aggregate_id=aggregate_id,
            version=version,
            data=data,
        )
        if aggregate_id not in self._snapshots:
            self._snapshots[aggregate_id] = []
        self._snapshots[aggregate_id].append(snapshot)
        return snapshot

    def get_latest(self, aggregate_id: str) -> Optional[Snapshot]:
        """Get the most recent snapshot for an aggregate."""
        snapshots = self._snapshots.get(aggregate_id, [])
        if not snapshots:
            return None
        return max(snapshots, key=lambda s: s.version)

    def get_at_version(self, aggregate_id: str,
                       version: int) -> Optional[Snapshot]:
        """Get a snapshot at a specific version."""
        snapshots = self._snapshots.get(aggregate_id, [])
        for snapshot in snapshots:
            if snapshot.version == version:
                return snapshot
        return None

    def has_snapshot(self, aggregate_id: str) -> bool:
        """Check if any snapshots exist for an aggregate."""
        return aggregate_id in self._snapshots and len(self._snapshots[aggregate_id]) > 0

    def delete_snapshots(self, aggregate_id: str) -> int:
        """Delete all snapshots for an aggregate. Returns count deleted."""
        if aggregate_id in self._snapshots:
            count = len(self._snapshots[aggregate_id])
            del self._snapshots[aggregate_id]
            return count
        return 0

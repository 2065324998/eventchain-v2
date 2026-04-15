"""Base event class for the event sourcing framework."""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Event:
    """Represents a domain event in the event store.

    Events are immutable records of something that happened in the domain.
    Each event belongs to an aggregate and has a monotonically increasing
    version number within that aggregate's stream.
    """

    aggregate_id: str
    event_type: str
    data: dict[str, Any]
    version: int = 0
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.aggregate_id:
            raise ValueError("aggregate_id cannot be empty")
        if not self.event_type:
            raise ValueError("event_type cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
            "data": self.data,
            "version": self.version,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Event":
        return cls(
            event_id=d["event_id"],
            aggregate_id=d["aggregate_id"],
            event_type=d["event_type"],
            data=d["data"],
            version=d["version"],
            timestamp=d["timestamp"],
            metadata=d.get("metadata", {}),
        )

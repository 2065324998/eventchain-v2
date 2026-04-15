"""Tests for the EventUpcaster class."""

from eventchain.event import Event
from eventchain.versioning import EventUpcaster


class TestEventUpcaster:
    def test_register_and_upcast(self):
        upcaster = EventUpcaster()
        upcaster.register(
            "OrderPlaced", 1, 2,
            lambda data: {**data, "currency": data.get("currency", "USD")}
        )

        event = Event("agg-1", "OrderPlaced", {"total": 100}, version=1,
                       metadata={"schema_version": 1})
        result = upcaster.upcast(event)

        assert result.data["currency"] == "USD"
        assert result.data["total"] == 100
        assert result.metadata["schema_version"] == 2

    def test_chain_upcasters(self):
        upcaster = EventUpcaster()
        upcaster.register("UserCreated", 1, 2,
                          lambda d: {**d, "email": d.get("email", "")})
        upcaster.register("UserCreated", 2, 3,
                          lambda d: {**d, "role": "member"})

        event = Event("agg-1", "UserCreated", {"name": "Alice"}, version=1,
                       metadata={"schema_version": 1})
        result = upcaster.upcast(event)

        assert result.data["name"] == "Alice"
        assert result.data["email"] == ""
        assert result.data["role"] == "member"
        assert result.metadata["schema_version"] == 3

    def test_no_upcaster_returns_same_event(self):
        upcaster = EventUpcaster()
        event = Event("agg-1", "Simple", {"x": 1}, version=1)
        result = upcaster.upcast(event)
        assert result.data == {"x": 1}

    def test_upcast_stream(self):
        upcaster = EventUpcaster()
        upcaster.register("Evt", 1, 2,
                          lambda d: {**d, "added": True})

        events = [
            Event("agg-1", "Evt", {"val": i}, version=i,
                  metadata={"schema_version": 1})
            for i in range(1, 4)
        ]
        result = upcaster.upcast_stream(events)
        assert all(e.data["added"] is True for e in result)
        assert len(result) == 3

    def test_upcast_preserves_event_identity(self):
        upcaster = EventUpcaster()
        upcaster.register("Test", 1, 2, lambda d: {**d, "new": True})

        event = Event("agg-1", "Test", {"old": True}, version=3,
                       metadata={"schema_version": 1})
        result = upcaster.upcast(event)

        assert result.event_id == event.event_id
        assert result.aggregate_id == event.aggregate_id
        assert result.version == event.version
        assert result.timestamp == event.timestamp

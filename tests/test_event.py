"""Tests for the Event class."""

import pytest
from eventchain.event import Event


class TestEvent:
    def test_create_event(self):
        event = Event(
            aggregate_id="agg-1",
            event_type="OrderCreated",
            data={"item": "widget", "quantity": 5},
            version=1,
        )
        assert event.aggregate_id == "agg-1"
        assert event.event_type == "OrderCreated"
        assert event.data["item"] == "widget"
        assert event.version == 1
        assert event.event_id is not None

    def test_event_to_dict(self):
        event = Event(
            aggregate_id="agg-1",
            event_type="OrderCreated",
            data={"total": 100},
            version=1,
        )
        d = event.to_dict()
        assert d["aggregate_id"] == "agg-1"
        assert d["event_type"] == "OrderCreated"
        assert d["data"]["total"] == 100
        assert d["version"] == 1

    def test_event_from_dict(self):
        d = {
            "event_id": "evt-123",
            "aggregate_id": "agg-1",
            "event_type": "ItemAdded",
            "data": {"name": "widget"},
            "version": 3,
            "timestamp": "2024-01-01T00:00:00",
            "metadata": {"source": "test"},
        }
        event = Event.from_dict(d)
        assert event.event_id == "evt-123"
        assert event.aggregate_id == "agg-1"
        assert event.version == 3
        assert event.metadata["source"] == "test"

    def test_event_roundtrip(self):
        original = Event(
            aggregate_id="agg-1",
            event_type="Updated",
            data={"field": "name", "value": "new"},
            version=5,
            metadata={"user": "alice"},
        )
        restored = Event.from_dict(original.to_dict())
        assert restored.aggregate_id == original.aggregate_id
        assert restored.event_type == original.event_type
        assert restored.data == original.data
        assert restored.version == original.version

    def test_event_empty_aggregate_id_raises(self):
        with pytest.raises(ValueError, match="aggregate_id"):
            Event(aggregate_id="", event_type="Test", data={})

    def test_event_empty_event_type_raises(self):
        with pytest.raises(ValueError, match="event_type"):
            Event(aggregate_id="agg-1", event_type="", data={})

    def test_event_default_metadata(self):
        event = Event(
            aggregate_id="agg-1",
            event_type="Test",
            data={},
        )
        assert event.metadata == {}

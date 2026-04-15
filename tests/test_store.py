"""Tests for the EventStore class."""

from eventchain.store import EventStore


class TestEventStore:
    def test_append_event(self):
        store = EventStore()
        event = store.append("agg-1", "Created", {"name": "test"})
        assert event.aggregate_id == "agg-1"
        assert event.event_type == "Created"
        assert event.version == 1

    def test_append_increments_version(self):
        store = EventStore()
        e1 = store.append("agg-1", "Created", {})
        e2 = store.append("agg-1", "Updated", {})
        e3 = store.append("agg-1", "Updated", {})
        assert e1.version == 1
        assert e2.version == 2
        assert e3.version == 3

    def test_get_all_events(self):
        store = EventStore()
        store.append("agg-1", "Created", {})
        store.append("agg-1", "Updated", {"x": 1})
        store.append("agg-1", "Updated", {"x": 2})
        events = store.get_all_events("agg-1")
        assert len(events) == 3
        assert events[0].version == 1
        assert events[2].version == 3

    def test_get_all_events_empty(self):
        store = EventStore()
        events = store.get_all_events("nonexistent")
        assert events == []

    def test_separate_streams(self):
        store = EventStore()
        store.append("agg-1", "Created", {})
        store.append("agg-2", "Created", {})
        store.append("agg-1", "Updated", {})
        assert len(store.get_all_events("agg-1")) == 2
        assert len(store.get_all_events("agg-2")) == 1

    def test_get_latest_version(self):
        store = EventStore()
        store.append("agg-1", "Created", {})
        store.append("agg-1", "Updated", {})
        assert store.get_latest_version("agg-1") == 2

    def test_get_latest_version_empty(self):
        store = EventStore()
        assert store.get_latest_version("nonexistent") == 0

    def test_stream_exists(self):
        store = EventStore()
        assert not store.stream_exists("agg-1")
        store.append("agg-1", "Created", {})
        assert store.stream_exists("agg-1")

    def test_event_count(self):
        store = EventStore()
        store.append("agg-1", "A", {})
        store.append("agg-1", "B", {})
        assert store.get_event_count("agg-1") == 2
        assert store.get_event_count("nonexistent") == 0

    def test_append_with_metadata(self):
        store = EventStore()
        event = store.append("agg-1", "Created", {"x": 1},
                             metadata={"user": "alice"})
        assert event.metadata["user"] == "alice"

    def test_get_events_min_version_inclusive(self):
        """get_events with min_version returns events at and above that version."""
        store = EventStore()
        store.append("agg-1", "A", {})  # v1
        store.append("agg-1", "B", {})  # v2
        store.append("agg-1", "C", {})  # v3
        store.append("agg-1", "D", {})  # v4

        events = store.get_events("agg-1", min_version=2)
        assert len(events) == 3
        assert events[0].version == 2
        assert events[1].version == 3
        assert events[2].version == 4

    def test_get_events_min_version_zero_returns_all(self):
        """min_version=0 returns all events since versions start at 1."""
        store = EventStore()
        store.append("agg-1", "A", {})
        store.append("agg-1", "B", {})
        events = store.get_events("agg-1", min_version=0)
        assert len(events) == 2

    def test_get_events_min_version_beyond_latest(self):
        """min_version beyond latest version returns empty list."""
        store = EventStore()
        store.append("agg-1", "A", {})  # v1
        events = store.get_events("agg-1", min_version=5)
        assert len(events) == 0

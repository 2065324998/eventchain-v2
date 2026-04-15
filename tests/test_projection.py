"""Tests for the Projection class."""

from eventchain.store import EventStore
from eventchain.event import Event
from eventchain.projection import Projection


class TestProjection:
    def test_register_and_process(self):
        proj = Projection()
        proj.when("OrderPlaced", lambda e, s: s.update({"total_orders": s.get("total_orders", 0) + 1}))

        proj.process(Event("agg-1", "OrderPlaced", {"item": "A"}, version=1))
        proj.process(Event("agg-2", "OrderPlaced", {"item": "B"}, version=1))

        assert proj.state["total_orders"] == 2
        assert proj.processed_count == 2

    def test_multiple_handlers_for_same_type(self):
        proj = Projection()
        proj.when("Sale", lambda e, s: s.update({"count": s.get("count", 0) + 1}))
        proj.when("Sale", lambda e, s: s.update({"revenue": s.get("revenue", 0) + e.data["amount"]}))

        proj.process(Event("agg-1", "Sale", {"amount": 50}, version=1))
        proj.process(Event("agg-1", "Sale", {"amount": 30}, version=2))

        assert proj.state["count"] == 2
        assert proj.state["revenue"] == 80

    def test_unregistered_event_type(self):
        proj = Projection()
        proj.when("TypeA", lambda e, s: s.update({"a": True}))
        proj.process(Event("agg-1", "TypeB", {}, version=1))
        assert "a" not in proj.state
        assert proj.processed_count == 1

    def test_process_all(self):
        proj = Projection()
        proj.when("Tick", lambda e, s: s.update({"ticks": s.get("ticks", 0) + 1}))

        events = [
            Event("agg-1", "Tick", {}, version=i)
            for i in range(1, 6)
        ]
        proj.process_all(events)
        assert proj.state["ticks"] == 5

    def test_build_from_store(self):
        store = EventStore()
        store.append("agg-1", "Created", {"name": "test"})
        store.append("agg-1", "Updated", {"field": "status", "value": "active"})

        proj = Projection()
        proj.when("Created", lambda e, s: s.update({"name": e.data["name"]}))
        proj.when("Updated", lambda e, s: s.update({e.data["field"]: e.data["value"]}))

        state = proj.build_from_store(store, "agg-1")
        assert state["name"] == "test"
        assert state["status"] == "active"

    def test_reset(self):
        proj = Projection()
        proj.when("X", lambda e, s: s.update({"x": True}))
        proj.process(Event("agg-1", "X", {}, version=1))
        assert proj.state["x"] is True

        proj.reset()
        assert proj.state == {}
        assert proj.processed_count == 0

    def test_get_with_default(self):
        proj = Projection()
        assert proj.get("missing", "default") == "default"
        assert proj.get("missing") is None

"""Tests for the AggregateRoot class."""

from eventchain.store import EventStore
from eventchain.aggregate import AggregateRoot
from eventchain.event import Event


class Counter(AggregateRoot):
    """Simple test aggregate that counts events."""

    def __init__(self):
        super().__init__()
        self.count = 0
        self.name = ""

    def apply_counter_created(self, event):
        self.name = event.data["name"]

    def apply_counter_incremented(self, event):
        self.count += event.data.get("amount", 1)

    def apply_counter_reset(self, event):
        self.count = 0


class TestAggregate:
    def test_create_aggregate(self):
        store = EventStore()
        counter = Counter()
        counter.create(store, "cnt-1", {"name": "my-counter"}, type("CounterCreated", (), {}))
        assert counter.aggregate_id == "cnt-1"
        assert counter.name == "my-counter"
        assert counter.version == 1

    def test_apply_events(self):
        store = EventStore()
        counter = Counter()

        class CounterCreated:
            pass

        class CounterIncremented:
            pass

        counter.create(store, "cnt-1", {"name": "test"}, CounterCreated)
        counter.apply_event(store, "cnt-1", {"amount": 5}, CounterIncremented)
        counter.apply_event(store, "cnt-1", {"amount": 3}, CounterIncremented)

        assert counter.count == 8
        assert counter.version == 3

    def test_load_from_events(self):
        events = [
            Event("agg-1", "CounterCreated", {"name": "test"}, version=1),
            Event("agg-1", "CounterIncremented", {"amount": 10}, version=2),
            Event("agg-1", "CounterIncremented", {"amount": 20}, version=3),
        ]
        counter = Counter()
        counter.load_from_events(events)
        assert counter.count == 30
        assert counter.name == "test"
        assert counter.version == 3

    def test_take_snapshot(self):
        events = [
            Event("agg-1", "CounterCreated", {"name": "snap-test"}, version=1),
            Event("agg-1", "CounterIncremented", {"amount": 42}, version=2),
        ]
        counter = Counter()
        counter.load_from_events(events)
        snapshot = counter.take_snapshot()
        assert snapshot["count"] == 42
        assert snapshot["name"] == "snap-test"

    def test_restore_from_snapshot(self):
        counter = Counter()
        counter.load_from_snapshot({"count": 100, "name": "restored"}, version=5)
        assert counter.count == 100
        assert counter.name == "restored"
        assert counter.version == 5

    def test_snake_case_conversion(self):
        assert AggregateRoot._to_snake_case("CounterCreated") == "counter_created"
        assert AggregateRoot._to_snake_case("MoneyDeposited") == "money_deposited"
        assert AggregateRoot._to_snake_case("A") == "a"

    def test_unknown_event_type_ignored(self):
        events = [
            Event("agg-1", "UnknownEvent", {"x": 1}, version=1),
        ]
        counter = Counter()
        counter.load_from_events(events)
        assert counter.version == 1
        assert counter.count == 0

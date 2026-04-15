"""Tests for the ReplayEngine class."""

from eventchain.store import EventStore
from eventchain.aggregate import AggregateRoot
from eventchain.replay import ReplayEngine


class BankAccount(AggregateRoot):
    """Test aggregate for replay tests."""

    def __init__(self):
        super().__init__()
        self.balance = 0
        self.owner = ""
        self.transactions = []

    def apply_account_created(self, event):
        self.owner = event.data["owner"]

    def apply_money_deposited(self, event):
        self.balance += event.data["amount"]
        self.transactions.append(("deposit", event.data["amount"]))

    def apply_money_withdrawn(self, event):
        self.balance -= event.data["amount"]
        self.transactions.append(("withdrawal", event.data["amount"]))


class TestReplayEngine:
    def test_full_replay(self):
        store = EventStore()
        store.append("acc-1", "AccountCreated", {"owner": "Alice"})
        store.append("acc-1", "MoneyDeposited", {"amount": 100})
        store.append("acc-1", "MoneyDeposited", {"amount": 50})
        store.append("acc-1", "MoneyWithdrawn", {"amount": 30})

        engine = ReplayEngine(store)
        account = engine.rebuild("acc-1", BankAccount)

        assert account.owner == "Alice"
        assert account.balance == 120
        assert account.version == 4

    def test_replay_to_version(self):
        store = EventStore()
        store.append("acc-1", "AccountCreated", {"owner": "Bob"})
        store.append("acc-1", "MoneyDeposited", {"amount": 200})
        store.append("acc-1", "MoneyDeposited", {"amount": 300})
        store.append("acc-1", "MoneyWithdrawn", {"amount": 100})

        engine = ReplayEngine(store)
        account = engine.replay_to_version("acc-1", BankAccount, 2)

        assert account.balance == 200
        assert account.version == 2

    def test_replay_empty_stream(self):
        store = EventStore()
        engine = ReplayEngine(store)
        account = engine.rebuild("nonexistent", BankAccount)
        assert account.balance == 0
        assert account.version == 0

    def test_replay_preserves_transaction_log(self):
        store = EventStore()
        store.append("acc-1", "AccountCreated", {"owner": "Carol"})
        store.append("acc-1", "MoneyDeposited", {"amount": 50})
        store.append("acc-1", "MoneyWithdrawn", {"amount": 20})

        engine = ReplayEngine(store)
        account = engine.rebuild("acc-1", BankAccount)

        assert len(account.transactions) == 2
        assert account.transactions[0] == ("deposit", 50)
        assert account.transactions[1] == ("withdrawal", 20)

# EventChain

A lightweight event sourcing framework for Python applications.

## Features

- Event store with append-only semantics
- Aggregate root base class with automatic versioning
- Snapshot support for fast aggregate restoration
- Event replay and projection building
- Event versioning and upcasting

## Quick Start

```python
from eventchain import EventStore, AggregateRoot, Event

class AccountCreated(Event):
    pass

class MoneyDeposited(Event):
    pass

class BankAccount(AggregateRoot):
    def __init__(self):
        super().__init__()
        self.balance = 0
        self.owner = ""

    def apply_account_created(self, event):
        self.owner = event.data["owner"]

    def apply_money_deposited(self, event):
        self.balance += event.data["amount"]

# Create and use
store = EventStore()
account = BankAccount()
account.create(store, "acc-1", {"owner": "Alice"}, AccountCreated)
account.apply_event(store, "acc-1", {"amount": 100}, MoneyDeposited)
```

## Installation

```bash
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest -v
```

"""Exception classes for the event sourcing framework."""


class EventChainError(Exception):
    """Base exception for all EventChain errors."""
    pass


class ConcurrencyError(EventChainError):
    """Raised when a version conflict is detected during event append."""

    def __init__(self, aggregate_id: str, expected: int, actual: int):
        self.aggregate_id = aggregate_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Concurrency conflict for aggregate {aggregate_id}: "
            f"expected version {expected}, got {actual}"
        )


class AggregateNotFoundError(EventChainError):
    """Raised when an aggregate does not exist in the event store."""

    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        super().__init__(f"Aggregate not found: {aggregate_id}")


class InvalidEventError(EventChainError):
    """Raised when an event fails validation."""

    def __init__(self, message: str):
        super().__init__(message)


class SnapshotError(EventChainError):
    """Raised when snapshot operations fail."""

    def __init__(self, message: str):
        super().__init__(message)

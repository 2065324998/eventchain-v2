"""Event notification and webhook dispatch."""

from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from eventchain.event import Event


@dataclass
class Notification:
    """A notification generated from a domain event."""
    event_type: str
    aggregate_id: str
    message: str
    priority: str = "normal"  # low, normal, high, critical
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationRule:
    """A rule that generates notifications from events."""

    def __init__(self, event_type: str, priority: str = "normal",
                 condition: Optional[Callable[[Event], bool]] = None,
                 message_template: str = ""):
        self.event_type = event_type
        self.priority = priority
        self.condition = condition
        self.message_template = message_template

    def matches(self, event: Event) -> bool:
        """Check if this rule applies to the given event."""
        if event.event_type != self.event_type:
            return False
        if self.condition is not None:
            return self.condition(event)
        return True

    def create_notification(self, event: Event) -> Notification:
        """Create a notification from an event."""
        message = self.message_template.format(
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            **event.data,
        )
        return Notification(
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            message=message,
            priority=self.priority,
            metadata={"event_id": event.event_id},
        )


class NotificationDispatcher:
    """Dispatches notifications based on registered rules."""

    def __init__(self):
        self._rules: list[NotificationRule] = []
        self._handlers: list[Callable[[Notification], None]] = []
        self._history: list[Notification] = []

    def add_rule(self, rule: NotificationRule) -> None:
        """Register a notification rule."""
        self._rules.append(rule)

    def add_handler(self, handler: Callable[[Notification], None]) -> None:
        """Register a notification handler (e.g., email, webhook)."""
        self._handlers.append(handler)

    def process_event(self, event: Event) -> list[Notification]:
        """Process an event through all rules and dispatch notifications."""
        notifications = []
        for rule in self._rules:
            if rule.matches(event):
                notification = rule.create_notification(event)
                notifications.append(notification)
                self._history.append(notification)
                for handler in self._handlers:
                    handler(notification)
        return notifications

    def get_history(self, event_type: Optional[str] = None) -> list[Notification]:
        """Get notification history, optionally filtered by event type."""
        if event_type is None:
            return list(self._history)
        return [n for n in self._history if n.event_type == event_type]

    def clear_history(self) -> None:
        """Clear notification history."""
        self._history.clear()

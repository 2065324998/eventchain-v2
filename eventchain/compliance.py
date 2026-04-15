"""Compliance and regulatory reporting utilities."""

from decimal import Decimal
from typing import Any
from datetime import datetime

from eventchain.event import Event


# Reporting thresholds
LARGE_TRANSACTION_THRESHOLD = Decimal("10000")
DAILY_LIMIT = Decimal("50000")
SUSPICIOUS_PATTERN_WINDOW = 5  # number of transactions to check


class ComplianceReport:
    """Generates compliance reports from account events."""

    def __init__(self):
        self.large_transactions: list[dict[str, Any]] = []
        self.daily_totals: dict[str, Decimal] = {}
        self.limit_breaches: list[dict[str, Any]] = []
        self.flagged_patterns: list[str] = []

    def process_event(self, event: Event) -> None:
        """Process an event for compliance reporting."""
        if event.event_type in ("MoneyDeposited", "MoneyWithdrawn"):
            amount = Decimal(str(event.data.get("amount", "0")))
            self._check_large_transaction(event, amount)
            self._update_daily_total(event, amount)

    def _check_large_transaction(self, event: Event,
                                  amount: Decimal) -> None:
        """Flag transactions above the reporting threshold."""
        if amount >= LARGE_TRANSACTION_THRESHOLD:
            self.large_transactions.append({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "amount": amount,
                "timestamp": event.timestamp,
            })

    def _update_daily_total(self, event: Event,
                            amount: Decimal) -> None:
        """Track daily transaction totals for limit monitoring."""
        date_str = event.timestamp[:10]  # YYYY-MM-DD
        current = self.daily_totals.get(date_str, Decimal("0"))
        self.daily_totals[date_str] = current + amount

        if self.daily_totals[date_str] > DAILY_LIMIT:
            self.limit_breaches.append({
                "date": date_str,
                "total": self.daily_totals[date_str],
                "triggering_event": event.event_id,
            })

    def check_structuring(self, events: list[Event],
                          window: int = SUSPICIOUS_PATTERN_WINDOW) -> bool:
        """Detect potential structuring (splitting transactions to avoid
        reporting thresholds).

        Checks if multiple transactions just below the threshold occur
        within a short window.
        """
        amounts = []
        for event in events:
            if event.event_type in ("MoneyDeposited", "MoneyWithdrawn"):
                amount = Decimal(str(event.data.get("amount", "0")))
                amounts.append(amount)

        if len(amounts) < window:
            return False

        # Check if the last N transactions are all between 80-100% of threshold
        recent = amounts[-window:]
        lower = LARGE_TRANSACTION_THRESHOLD * Decimal("0.8")
        suspicious_count = sum(
            1 for a in recent
            if lower <= a < LARGE_TRANSACTION_THRESHOLD
        )

        if suspicious_count >= window - 1:
            self.flagged_patterns.append(
                f"Potential structuring: {suspicious_count}/{window} "
                f"transactions near threshold"
            )
            return True

        return False

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of compliance findings."""
        return {
            "large_transactions": len(self.large_transactions),
            "limit_breaches": len(self.limit_breaches),
            "flagged_patterns": len(self.flagged_patterns),
        }

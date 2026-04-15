"""Transaction limit enforcement."""

from decimal import Decimal
from typing import Optional


# Per-transaction limits by account type
TRANSACTION_LIMITS = {
    "standard": {
        "max_single_deposit": Decimal("25000"),
        "max_single_withdrawal": Decimal("10000"),
        "max_daily_volume": Decimal("50000"),
    },
    "premium": {
        "max_single_deposit": Decimal("100000"),
        "max_single_withdrawal": Decimal("50000"),
        "max_daily_volume": Decimal("200000"),
    },
    "business": {
        "max_single_deposit": Decimal("500000"),
        "max_single_withdrawal": Decimal("250000"),
        "max_daily_volume": Decimal("1000000"),
    },
}


class TransactionLimitError(Exception):
    """Raised when a transaction would exceed limits."""

    def __init__(self, limit_type: str, amount: Decimal,
                 limit: Decimal):
        self.limit_type = limit_type
        self.amount = amount
        self.limit = limit
        super().__init__(
            f"Transaction limit exceeded: {limit_type}. "
            f"Amount: {amount}, Limit: {limit}"
        )


def get_limits(account_type: str) -> dict[str, Decimal]:
    """Get transaction limits for an account type."""
    return TRANSACTION_LIMITS.get(
        account_type,
        TRANSACTION_LIMITS["standard"]
    )


def check_deposit_limit(amount: Decimal,
                        account_type: str = "standard") -> Optional[str]:
    """Check if a deposit amount exceeds the limit.

    Returns None if within limits, or an error message if exceeded.
    """
    limits = get_limits(account_type)
    if amount > limits["max_single_deposit"]:
        return (
            f"Deposit of {amount} exceeds maximum of "
            f"{limits['max_single_deposit']} for {account_type} accounts"
        )
    return None


def check_withdrawal_limit(amount: Decimal,
                           account_type: str = "standard") -> Optional[str]:
    """Check if a withdrawal amount exceeds the limit."""
    limits = get_limits(account_type)
    if amount > limits["max_single_withdrawal"]:
        return (
            f"Withdrawal of {amount} exceeds maximum of "
            f"{limits['max_single_withdrawal']} for {account_type} accounts"
        )
    return None


def check_daily_volume(current_daily_volume: Decimal, new_amount: Decimal,
                       account_type: str = "standard") -> Optional[str]:
    """Check if adding this transaction would exceed the daily volume limit."""
    limits = get_limits(account_type)
    projected = current_daily_volume + new_amount
    if projected > limits["max_daily_volume"]:
        return (
            f"Daily volume of {projected} would exceed maximum of "
            f"{limits['max_daily_volume']} for {account_type} accounts"
        )
    return None

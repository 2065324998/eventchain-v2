"""Multi-currency bank account aggregate with transaction ledger."""

from typing import Any
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

from eventchain.aggregate import AggregateRoot
from eventchain.event import Event
from eventchain.currency import to_usd


class LedgerEntry:
    """A single entry in the account's transaction ledger."""

    __slots__ = ("event_version", "entry_type", "currency", "amount",
                 "fee", "net_amount", "description", "running_balance")

    def __init__(self, event_version: int, entry_type: str, currency: str,
                 amount: Decimal, fee: Decimal, net_amount: Decimal,
                 description: str, running_balance: Decimal):
        self.event_version = event_version
        self.entry_type = entry_type
        self.currency = currency
        self.amount = amount
        self.fee = fee
        self.net_amount = net_amount
        self.description = description
        self.running_balance = running_balance

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_version": self.event_version,
            "entry_type": self.entry_type,
            "currency": self.currency,
            "amount": str(self.amount),
            "fee": str(self.fee),
            "net_amount": str(self.net_amount),
            "description": self.description,
            "running_balance": str(self.running_balance),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LedgerEntry":
        return cls(
            event_version=d["event_version"],
            entry_type=d["entry_type"],
            currency=d["currency"],
            amount=Decimal(d["amount"]),
            fee=Decimal(d["fee"]),
            net_amount=Decimal(d["net_amount"]),
            description=d["description"],
            running_balance=Decimal(d["running_balance"]),
        )


# Fee tiers based on cumulative USD-equivalent transaction volume.
# Higher volume = lower fees (loyalty discount).
FEE_TIERS = [
    (Decimal("10000"), Decimal("0.003")),   # 0-10k:   0.3%
    (Decimal("50000"), Decimal("0.002")),   # 10k-50k: 0.2%
    (Decimal("100000"), Decimal("0.001")),  # 50k-100k: 0.1%
    (Decimal("Infinity"), Decimal("0.0005")), # 100k+: 0.05%
]


def get_fee_rate(cumulative_volume_usd: Decimal) -> Decimal:
    """Get the fee rate based on cumulative USD-equivalent volume.

    The volume parameter should be the total transaction volume converted
    to USD using current exchange rates.
    """
    for threshold, rate in FEE_TIERS:
        if cumulative_volume_usd < threshold:
            return rate
    return FEE_TIERS[-1][1]


def calculate_fee(amount: Decimal, currency: str,
                  cumulative_volume_usd: Decimal) -> Decimal:
    """Calculate the transaction fee.

    The fee rate is determined by the cumulative USD-equivalent volume,
    but applied to the transaction amount in its native currency.
    """
    rate = get_fee_rate(cumulative_volume_usd)
    fee = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return fee


class BankAccount(AggregateRoot):
    """Multi-currency bank account with tiered fees and transaction ledger.

    Fee rates decrease as the account's cumulative transaction volume
    (converted to USD equivalent) increases through loyalty tiers.
    """

    def __init__(self):
        super().__init__()
        self.owner: str = ""
        self.account_type: str = "standard"
        self.balances: dict[str, Decimal] = {}
        self.ledger: list[dict] = []
        self.total_fees_paid: Decimal = Decimal("0")
        self.cumulative_volume_usd: Decimal = Decimal("0")
        self.transaction_count: int = 0
        self.is_active: bool = True

    def get_balance(self, currency: str = "USD") -> Decimal:
        """Get balance for a specific currency."""
        return self.balances.get(currency, Decimal("0"))

    def get_ledger_entries(self) -> list[LedgerEntry]:
        """Get ledger entries as LedgerEntry objects."""
        return [LedgerEntry.from_dict(d) for d in self.ledger]

    # --- Event Handlers ---

    def apply_account_opened(self, event: Event) -> None:
        self.owner = event.data["owner"]
        self.account_type = event.data.get("account_type", "standard")

    def apply_money_deposited(self, event: Event) -> None:
        amount = Decimal(str(event.data["amount"]))
        currency = event.data.get("currency", "USD")
        description = event.data.get("description", "Deposit")

        # Fee based on cumulative volume BEFORE this transaction
        fee = calculate_fee(amount, currency, self.cumulative_volume_usd)
        net = amount - fee

        # Update cumulative volume in USD equivalent
        self.cumulative_volume_usd += to_usd(amount, currency)

        self.balances[currency] = self.get_balance(currency) + net
        self.total_fees_paid += fee
        self.transaction_count += 1

        self.ledger.append(LedgerEntry(
            event_version=event.version,
            entry_type="deposit",
            currency=currency,
            amount=amount,
            fee=fee,
            net_amount=net,
            description=description,
            running_balance=self.get_balance(currency),
        ).to_dict())

    def apply_money_withdrawn(self, event: Event) -> None:
        amount = Decimal(str(event.data["amount"]))
        currency = event.data.get("currency", "USD")
        description = event.data.get("description", "Withdrawal")

        # Convert to USD equivalent for volume tracking and fee calculation
        amount_usd = to_usd(amount, currency)

        # Fee based on volume before this transaction
        fee = calculate_fee(amount_usd, currency, self.cumulative_volume_usd)

        self.cumulative_volume_usd += amount_usd
        total_debit = amount + fee

        self.balances[currency] = self.get_balance(currency) - total_debit
        self.total_fees_paid += fee
        self.transaction_count += 1

        self.ledger.append(LedgerEntry(
            event_version=event.version,
            entry_type="withdrawal",
            currency=currency,
            amount=amount,
            fee=fee,
            net_amount=total_debit,
            description=description,
            running_balance=self.get_balance(currency),
        ).to_dict())

    def apply_refund_issued(self, event: Event) -> None:
        amount = Decimal(str(event.data["amount"]))
        currency = event.data.get("currency", "USD")
        original_fee = Decimal(str(event.data.get("original_fee", "0")))
        description = event.data.get("description", "Refund")

        refund_total = amount + original_fee

        self.balances[currency] = self.get_balance(currency) + refund_total
        self.total_fees_paid -= original_fee
        self.transaction_count += 1

        self.ledger.append(LedgerEntry(
            event_version=event.version,
            entry_type="refund",
            currency=currency,
            amount=amount,
            fee=-original_fee,
            net_amount=refund_total,
            description=description,
            running_balance=self.get_balance(currency),
        ).to_dict())

    def apply_account_closed(self, event: Event) -> None:
        self.is_active = False

    def apply_fee_waiver_applied(self, event: Event) -> None:
        """Apply a fee waiver — credits back a previously charged fee."""
        amount = Decimal(str(event.data["amount"]))
        currency = event.data.get("currency", "USD")

        self.balances[currency] = self.get_balance(currency) + amount
        self.total_fees_paid -= amount
        self.transaction_count += 1

        self.ledger.append(LedgerEntry(
            event_version=event.version,
            entry_type="fee_waiver",
            currency=currency,
            amount=amount,
            fee=Decimal("0"),
            net_amount=amount,
            description=event.data.get("description", "Fee waiver"),
            running_balance=self.get_balance(currency),
        ).to_dict())

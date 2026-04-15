"""Currency conversion and exchange rate management."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from datetime import datetime, timezone


# Historical exchange rates (simplified — in production these would come
# from an external service). Rates are relative to USD.
EXCHANGE_RATES = {
    "USD": Decimal("1.0"),
    "EUR": Decimal("1.08"),    # 1 EUR = 1.08 USD
    "GBP": Decimal("1.27"),    # 1 GBP = 1.27 USD
    "JPY": Decimal("0.0067"),  # 1 JPY = 0.0067 USD
    "CHF": Decimal("1.12"),    # 1 CHF = 1.12 USD
    "CAD": Decimal("0.74"),    # 1 CAD = 0.74 USD
    "AUD": Decimal("0.65"),    # 1 AUD = 0.65 USD
}


def get_rate(from_currency: str, to_currency: str = "USD") -> Decimal:
    """Get the exchange rate from one currency to another.

    All rates go through USD as the base currency.
    """
    if from_currency == to_currency:
        return Decimal("1.0")

    from_to_usd = EXCHANGE_RATES.get(from_currency)
    to_to_usd = EXCHANGE_RATES.get(to_currency)

    if from_to_usd is None:
        raise ValueError(f"Unknown currency: {from_currency}")
    if to_to_usd is None:
        raise ValueError(f"Unknown currency: {to_currency}")

    # Convert: amount_from * from_to_usd / to_to_usd = amount_to
    return (from_to_usd / to_to_usd).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )


def convert(amount: Decimal, from_currency: str,
            to_currency: str = "USD") -> Decimal:
    """Convert an amount from one currency to another."""
    rate = get_rate(from_currency, to_currency)
    return (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_usd(amount: Decimal, currency: str) -> Decimal:
    """Convert any amount to USD equivalent."""
    return convert(amount, currency, "USD")


def get_usd_equivalent_volume(balances: dict[str, Decimal]) -> Decimal:
    """Calculate total portfolio value in USD across all currencies.

    This is used for fee tier calculations — the cumulative volume
    across all currencies determines the customer's loyalty tier.
    """
    total = Decimal("0")
    for currency, balance in balances.items():
        total += to_usd(abs(balance), currency)
    return total


class ExchangeRateProvider:
    """Provides exchange rates with caching and staleness detection."""

    def __init__(self):
        self._cache: dict[str, tuple[Decimal, datetime]] = {}
        self._cache_ttl_seconds: int = 3600

    def get_rate(self, from_currency: str,
                 to_currency: str = "USD") -> Decimal:
        """Get rate with caching."""
        cache_key = f"{from_currency}/{to_currency}"
        now = datetime.now(timezone.utc)

        if cache_key in self._cache:
            rate, cached_at = self._cache[cache_key]
            age = (now - cached_at).total_seconds()
            if age < self._cache_ttl_seconds:
                return rate

        rate = get_rate(from_currency, to_currency)
        self._cache[cache_key] = (rate, now)
        return rate

    def invalidate(self) -> None:
        """Clear the rate cache."""
        self._cache.clear()

    def is_stale(self, from_currency: str,
                 to_currency: str = "USD") -> bool:
        """Check if a cached rate is stale."""
        cache_key = f"{from_currency}/{to_currency}"
        if cache_key not in self._cache:
            return True
        _, cached_at = self._cache[cache_key]
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        return age >= self._cache_ttl_seconds

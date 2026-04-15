"""Tests for the BankAccount aggregate."""

from decimal import Decimal

from eventchain.store import EventStore
from eventchain.event import Event
from eventchain.account import BankAccount, calculate_fee, get_fee_rate, LedgerEntry


class TestFeeCalculation:
    def test_tier1_fee_rate(self):
        rate = get_fee_rate(Decimal("0"))
        assert rate == Decimal("0.003")

    def test_tier2_fee_rate(self):
        rate = get_fee_rate(Decimal("15000"))
        assert rate == Decimal("0.002")

    def test_tier3_fee_rate(self):
        rate = get_fee_rate(Decimal("75000"))
        assert rate == Decimal("0.001")

    def test_tier4_fee_rate(self):
        rate = get_fee_rate(Decimal("200000"))
        assert rate == Decimal("0.0005")

    def test_fee_at_boundary(self):
        rate = get_fee_rate(Decimal("9999"))
        assert rate == Decimal("0.003")
        rate = get_fee_rate(Decimal("10000"))
        assert rate == Decimal("0.002")

    def test_calculate_fee_tier1(self):
        fee = calculate_fee(Decimal("1000"), "USD", Decimal("0"))
        assert fee == Decimal("3.00")

    def test_fee_rounding(self):
        fee = calculate_fee(Decimal("333"), "USD", Decimal("0"))
        assert fee == Decimal("1.00")


class TestBankAccount:
    def test_open_account(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Alice"}, version=1),
        ]
        account.load_from_events(events)
        assert account.owner == "Alice"
        assert account.is_active is True

    def test_single_deposit(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Alice"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "1000", "currency": "USD"
            }, version=2),
        ]
        account.load_from_events(events)
        assert account.get_balance("USD") == Decimal("997.00")
        assert account.total_fees_paid == Decimal("3.00")
        assert account.cumulative_volume_usd == Decimal("1000")

    def test_multiple_deposits_tier1(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Bob"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "2000", "currency": "USD"
            }, version=2),
            Event("acc-1", "MoneyDeposited", {
                "amount": "3000", "currency": "USD"
            }, version=3),
        ]
        account.load_from_events(events)
        assert account.get_balance("USD") == Decimal("4985.00")
        assert account.cumulative_volume_usd == Decimal("5000")

    def test_deposit_crossing_tier_boundary(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Carol"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "9000", "currency": "USD"
            }, version=2),
            Event("acc-1", "MoneyDeposited", {
                "amount": "2000", "currency": "USD"
            }, version=3),
        ]
        account.load_from_events(events)
        assert account.get_balance("USD") == Decimal("10967.00")
        assert account.cumulative_volume_usd == Decimal("11000")

    def test_refund(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Dave"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "500", "currency": "USD"
            }, version=2),
            Event("acc-1", "RefundIssued", {
                "amount": "100", "currency": "USD",
                "original_fee": "0.30",
            }, version=3),
        ]
        account.load_from_events(events)
        assert account.get_balance("USD") == Decimal("598.80")

    def test_ledger_entries(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Eve"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "100", "currency": "USD", "description": "Paycheck"
            }, version=2),
        ]
        account.load_from_events(events)
        entries = account.get_ledger_entries()
        assert len(entries) == 1
        assert entries[0].description == "Paycheck"

    def test_fee_waiver(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Frank"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "1000", "currency": "USD"
            }, version=2),
            Event("acc-1", "FeeWaiverApplied", {
                "amount": "3.00", "currency": "USD",
            }, version=3),
        ]
        account.load_from_events(events)
        assert account.get_balance("USD") == Decimal("1000.00")

    def test_close_account(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Grace"}, version=1),
            Event("acc-1", "AccountClosed", {}, version=2),
        ]
        account.load_from_events(events)
        assert account.is_active is False

    def test_ledger_entry_roundtrip(self):
        entry = LedgerEntry(
            event_version=1, entry_type="deposit", currency="USD",
            amount=Decimal("100"), fee=Decimal("0.30"),
            net_amount=Decimal("99.70"), description="Test",
            running_balance=Decimal("99.70"),
        )
        restored = LedgerEntry.from_dict(entry.to_dict())
        assert restored.amount == entry.amount
        assert restored.fee == entry.fee

    def test_eur_deposit_volume_in_usd(self):
        """EUR deposits should track volume in USD equivalent."""
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Hank"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "1000", "currency": "EUR"
            }, version=2),
        ]
        account.load_from_events(events)
        # 1000 EUR = 1080 USD equivalent
        assert account.cumulative_volume_usd == Decimal("1080.00")

    def test_multi_currency_deposits(self):
        account = BankAccount()
        events = [
            Event("acc-1", "AccountOpened", {"owner": "Ivy"}, version=1),
            Event("acc-1", "MoneyDeposited", {
                "amount": "1000", "currency": "USD"
            }, version=2),
            Event("acc-1", "MoneyDeposited", {
                "amount": "500", "currency": "EUR"
            }, version=3),
        ]
        account.load_from_events(events)
        assert account.get_balance("USD") == Decimal("997.00")
        # EUR deposit: vol was 1000 USD (tier1), fee = 500*0.003 = 1.50
        assert account.get_balance("EUR") == Decimal("498.50")
        # Total volume: 1000 USD + 540 EUR->USD = 1540
        assert account.cumulative_volume_usd == Decimal("1540.00")

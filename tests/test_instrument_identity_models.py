"""
Tests for the canonical market-instrument identity contract.
"""

import pytest

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)


def test_instrument_identity_normalizes_provider_independent_fields() -> None:
    identity = InstrumentIdentity(
        symbol=" world ",
        name=" MSCI World ETF ",
        instrument_type=" etf ",
        currency=" eur ",
        isin=" ie00b4l5y983 ",
        exchange_ticker=" iwda ",
    )

    assert identity.symbol == "WORLD"
    assert identity.name == "MSCI World ETF"
    assert identity.instrument_type == "ETF"
    assert identity.currency == "EUR"
    assert identity.isin == "IE00B4L5Y983"
    assert identity.exchange_ticker == "IWDA"
    assert identity.instrument_key == "IE00B4L5Y983"


def test_instrument_identity_serializes_stable_key() -> None:
    identity = InstrumentIdentity(
        symbol="MSFT",
        name="Microsoft",
        instrument_type="STOCK",
        currency="USD",
        exchange_ticker="MSFT",
    )

    assert identity.to_dict() == {
        "symbol": "MSFT",
        "name": "Microsoft",
        "instrument_type": "STOCK",
        "currency": "USD",
        "isin": None,
        "exchange_ticker": "MSFT",
        "exchange_code": None,
        "instrument_key": "MSFT",
    }


def test_instrument_identity_scopes_ticker_by_exchange() -> None:
    identity = InstrumentIdentity(
        symbol="VUSA",
        name="Vanguard S&P 500 ETF",
        instrument_type="ETF",
        currency="GBP",
        isin="IE00B3XXRP09",
        exchange_ticker="VUSA",
        exchange_code="XLON",
    )

    assert identity.exchange_code == "XLON"
    assert identity.instrument_key == "IE00B3XXRP09"


def test_exchange_scoped_ticker_is_key_without_isin() -> None:
    identity = InstrumentIdentity(
        symbol="MSFT",
        name="Microsoft",
        instrument_type="STOCK",
        currency="USD",
        exchange_ticker="MSFT",
        exchange_code="XNAS",
    )

    assert identity.instrument_key == "XNAS:MSFT"


def test_exchange_code_requires_exchange_ticker() -> None:
    with pytest.raises(ValueError, match="requires exchange_ticker"):
        InstrumentIdentity(
            symbol="MSFT",
            name="Microsoft",
            instrument_type="STOCK",
            currency="USD",
            exchange_code="XNAS",
        )


@pytest.mark.parametrize("currency", ["EU", "EURO", "12A"])
def test_instrument_identity_rejects_invalid_currency(
    currency: str,
) -> None:
    with pytest.raises(ValueError, match="currency"):
        InstrumentIdentity(
            symbol="MSFT",
            name="Microsoft",
            instrument_type="STOCK",
            currency=currency,
        )


def test_instrument_identity_rejects_whitespace_in_exchange_ticker() -> None:
    with pytest.raises(ValueError, match="exchange_ticker"):
        InstrumentIdentity(
            symbol="MSFT",
            name="Microsoft",
            instrument_type="STOCK",
            currency="USD",
            exchange_ticker="US MSFT",
        )


def test_instrument_identity_requires_isin_for_fund_like_assets() -> None:
    with pytest.raises(ValueError, match="must provide an ISIN"):
        InstrumentIdentity(
            symbol="IWDA",
            name="MSCI World ETF",
            instrument_type="ETF",
            currency="EUR",
        )

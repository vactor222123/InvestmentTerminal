"""
Tests for exchange, calendar, and currency metadata contracts.
"""

import pytest

from investment_terminal.market.market_metadata_models import (
    CurrencyMetadata,
    ExchangeMetadata,
    TradingCalendarMetadata,
)


def calendar() -> TradingCalendarMetadata:
    return TradingCalendarMetadata(
        calendar_id="xetra",
        timezone="Europe/Berlin",
        version=1,
        source="exchange_fixture",
    )


def test_currency_metadata_normalizes_and_serializes() -> None:
    currency = CurrencyMetadata(
        code=" eur ",
        name=" Euro ",
        minor_unit=2,
    )

    assert currency.to_dict() == {
        "code": "EUR",
        "name": "Euro",
        "minor_unit": 2,
    }


def test_trading_calendar_preserves_versioned_provenance() -> None:
    metadata = calendar()

    assert metadata.identity_key == "XETRA@1"
    assert metadata.to_dict() == {
        "calendar_id": "XETRA",
        "version": 1,
        "identity_key": "XETRA@1",
        "timezone": "Europe/Berlin",
        "source": "EXCHANGE_FIXTURE",
    }


def test_exchange_metadata_normalizes_supported_currencies() -> None:
    exchange = ExchangeMetadata(
        exchange_code=" xetr ",
        name=" Deutsche Borse Xetra ",
        country_code=" de ",
        calendar=calendar(),
        currency_codes=("eur", "usd"),
    )

    assert exchange.supports_currency(" EUR ") is True
    assert exchange.supports_currency("GBP") is False
    assert exchange.to_dict()["currency_codes"] == ["EUR", "USD"]
    assert exchange.to_dict()["calendar"]["identity_key"] == "XETRA@1"


@pytest.mark.parametrize("timezone", ["", "Invalid/Timezone"])
def test_trading_calendar_rejects_invalid_timezone(
    timezone: str,
) -> None:
    with pytest.raises(ValueError, match="timezone"):
        TradingCalendarMetadata(
            calendar_id="XETRA",
            timezone=timezone,
            version=1,
            source="TEST",
        )


def test_exchange_metadata_rejects_duplicate_currency_codes() -> None:
    with pytest.raises(ValueError, match="unique"):
        ExchangeMetadata(
            exchange_code="XETR",
            name="Deutsche Borse Xetra",
            country_code="DE",
            calendar=calendar(),
            currency_codes=("EUR", "eur"),
        )


def test_exchange_metadata_requires_explicit_calendar_contract() -> None:
    with pytest.raises(TypeError, match="TradingCalendarMetadata"):
        ExchangeMetadata(
            exchange_code="XETR",
            name="Deutsche Borse Xetra",
            country_code="DE",
            calendar="XETRA",  # type: ignore[arg-type]
            currency_codes=("EUR",),
        )

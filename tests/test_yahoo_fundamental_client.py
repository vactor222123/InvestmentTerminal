"""
Tests for YahooFundamentalClient.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from investment_terminal.clients.yahoo_fundamental_client import (
    YahooFundamentalClient,
)
from investment_terminal.utils.exceptions import APIError


FIXED_TIME = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_info() -> dict[str, object]:
    return {
        "currency": "USD",
        "marketCap": 3_500_000_000_000,
        "enterpriseValue": 3_450_000_000_000,
        "trailingPE": 35.0,
        "forwardPE": 30.0,
        "pegRatio": 2.1,
        "priceToBook": 11.0,
        "priceToSalesTrailing12Months": 12.5,
        "enterpriseToEbitda": 24.0,
        "totalRevenue": 280_000_000_000,
        "revenueGrowth": 0.15,
        "earningsGrowth": 0.12,
        "trailingEps": 13.2,
        "forwardEps": 15.0,
        "grossMargins": 0.69,
        "operatingMargins": 0.44,
        "profitMargins": 0.36,
        "returnOnEquity": 0.33,
        "returnOnAssets": 0.15,
        "totalCash": 90_000_000_000,
        "totalDebt": 80_000_000_000,
        "debtToEquity": 35.0,
        "currentRatio": 1.35,
        "quickRatio": 1.15,
        "operatingCashflow": 130_000_000_000,
        "freeCashflow": 75_000_000_000,
        "dividendYield": 0.7,
        "payoutRatio": 0.25,
        "operatingIncome": 120_000_000_000,
        "effectiveTaxRate": 0.18,
        "totalStockholderEquity": 310_000_000_000,
    }


def create_client(
    info: object,
) -> tuple[YahooFundamentalClient, Mock]:
    ticker = Mock()
    ticker.info = info

    ticker_factory = Mock(
        return_value=ticker
    )

    client = YahooFundamentalClient(
        ticker_factory=ticker_factory,
        clock=lambda: FIXED_TIME,
    )

    return client, ticker_factory


def test_get_fundamentals_maps_provider_fields() -> None:
    client, ticker_factory = create_client(
        create_info()
    )

    result = client.get_fundamentals(
        symbol=" msft ",
        currency=" eur ",
    )

    assert result.symbol == "MSFT"
    assert result.currency == "USD"
    assert result.generated_at == FIXED_TIME

    assert result.market_cap == 3_500_000_000_000
    assert result.trailing_pe == 35.0
    assert result.forward_pe == 30.0
    assert result.revenue_growth == 0.15
    assert result.free_cash_flow == 75_000_000_000
    assert result.debt_to_equity == pytest.approx(
    0.35
)
    assert result.dividend_yield == pytest.approx(
    0.007
)

    assert result.data_quality is not None
    assert (
        result.data_quality.source
        == "Yahoo Finance"
    )

    ticker_factory.assert_called_once_with(
        "MSFT"
    )


def test_get_fundamentals_calculates_roic() -> None:
    client, _ = create_client(
        create_info()
    )

    result = client.get_fundamentals(
        "MSFT"
    )

    expected = (
        120_000_000_000
        * (1.0 - 0.18)
        / (
            80_000_000_000
            + 310_000_000_000
            - 90_000_000_000
        )
    )

    assert (
        result.return_on_invested_capital
        == pytest.approx(expected)
    )

def test_get_fundamentals_normalizes_percentage_points() -> None:
    info = create_info()
    info["dividendYield"] = 0.81
    info["debtToEquity"] = 29.118

    client, _ = create_client(info)

    result = client.get_fundamentals("MSFT")

    assert result.dividend_yield == pytest.approx(
        0.0081
    )
    assert result.debt_to_equity == pytest.approx(
        0.29118
    )

def test_get_fundamentals_uses_requested_currency_when_missing() -> None:
    info = create_info()
    info.pop("currency")

    client, _ = create_client(info)

    result = client.get_fundamentals(
        symbol="SAP.DE",
        currency="EUR",
    )

    assert result.currency == "EUR"


def test_get_fundamentals_converts_invalid_metrics_to_none() -> None:
    info = create_info()
    info["trailingPE"] = "not available"
    info["forwardPE"] = float("nan")
    info["marketCap"] = True

    client, _ = create_client(info)

    result = client.get_fundamentals(
        "MSFT"
    )

    assert result.trailing_pe is None
    assert result.forward_pe is None
    assert result.market_cap is None

    assert result.data_quality is not None
    assert (
        "trailing_pe"
        in result.data_quality.missing_fields
    )


def test_get_fundamentals_rejects_invalid_payload() -> None:
    client, _ = create_client(
        ["invalid", "payload"]
    )

    with pytest.raises(
        APIError,
        match="invalid fundamental data",
    ):
        client.get_fundamentals("MSFT")


def test_get_fundamentals_converts_provider_error() -> None:
    ticker_factory = Mock(
        side_effect=RuntimeError(
            "Provider failure"
        )
    )

    client = YahooFundamentalClient(
        ticker_factory=ticker_factory,
        clock=lambda: FIXED_TIME,
    )

    with pytest.raises(
        APIError,
        match="fundamental request failed",
    ):
        client.get_fundamentals("MSFT")


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "   ",
        None,
    ],
)
def test_get_fundamentals_rejects_invalid_symbol(
    symbol,
) -> None:
    client = YahooFundamentalClient(
        ticker_factory=Mock(),
        clock=lambda: FIXED_TIME,
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        client.get_fundamentals(symbol)


def test_get_fundamentals_is_json_ready() -> None:
    client, _ = create_client(
        create_info()
    )

    result = client.get_fundamentals(
        "MSFT"
    )

    payload = result.to_dict()

    assert payload["symbol"] == "MSFT"
    assert (
        payload["generated_at"]
        == "2026-08-01T12:00:00+00:00"
    )
    assert isinstance(
        payload["data_quality"]["missing_fields"],
        list,
    )
"""
Yahoo Finance fundamental-data client.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from math import isfinite
from numbers import Real
from typing import Any

import yfinance as yf

from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_data_quality_service import (
    FundamentalDataQualityService,
)
from investment_terminal.utils.exceptions import APIError


class YahooFundamentalClient:
    """
    Download and normalize fundamental data through yfinance.
    """

    FIELD_MAP = {
        "market_cap": "marketCap",
        "enterprise_value": "enterpriseValue",
        "trailing_pe": "trailingPE",
        "forward_pe": "forwardPE",
        "peg_ratio": "pegRatio",
        "price_to_book": "priceToBook",
        "price_to_sales": "priceToSalesTrailing12Months",
        "enterprise_to_ebitda": "enterpriseToEbitda",
        "revenue": "totalRevenue",
        "revenue_growth": "revenueGrowth",
        "earnings_growth": "earningsGrowth",
        "eps_trailing": "trailingEps",
        "eps_forward": "forwardEps",
        "gross_margin": "grossMargins",
        "operating_margin": "operatingMargins",
        "net_margin": "profitMargins",
        "return_on_equity": "returnOnEquity",
        "return_on_assets": "returnOnAssets",
        "total_cash": "totalCash",
        "total_debt": "totalDebt",
        "debt_to_equity": "debtToEquity",
        "current_ratio": "currentRatio",
        "quick_ratio": "quickRatio",
        "operating_cash_flow": "operatingCashflow",
        "free_cash_flow": "freeCashflow",
        "dividend_yield": "dividendYield",
        "payout_ratio": "payoutRatio",
    }

    @classmethod
    def _normalize_metric(
        cls,
        model_field: str,
        value: object,
    ) -> float | None:
        """
        Normalize provider-specific units into model conventions.
        """
        numeric_value = cls._optional_number(value)

        if numeric_value is None:
            return None

        percentage_point_fields = {
            "dividend_yield",
            "debt_to_equity",
        }

        if model_field in percentage_point_fields:
            return numeric_value / 100.0

        return numeric_value

    def __init__(
        self,
        ticker_factory: Callable[[str], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """
        Create the client with injectable external dependencies.
        """
        self._ticker_factory = ticker_factory or yf.Ticker
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

    def get_fundamentals(
        self,
        symbol: str,
        currency: str = "USD",
    ) -> FundamentalSnapshot:
        """
        Download and normalize one fundamental snapshot.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )

        fetched_at = self._clock()

        if not isinstance(fetched_at, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        try:
            ticker = self._ticker_factory(
                normalized_symbol
            )
            raw_info = ticker.info
        except Exception as exc:
            raise APIError(
                "Yahoo Finance fundamental request failed "
                f"for {normalized_symbol}."
            ) from exc

        if not isinstance(raw_info, dict):
            raise APIError(
                "Yahoo Finance returned invalid fundamental data."
            )

        provider_currency = raw_info.get("currency")

        if (
            isinstance(provider_currency, str)
            and provider_currency.strip()
        ):
            normalized_currency = (
                provider_currency.strip().upper()
            )

        values = {
    model_field: self._normalize_metric(
        model_field=model_field,
        value=raw_info.get(provider_field),
    )
    for model_field, provider_field
    in self.FIELD_MAP.items()
}

        return_on_invested_capital = (
            self._calculate_roic(raw_info)
        )

        snapshot = FundamentalSnapshot(
            symbol=normalized_symbol,
            currency=normalized_currency,
            generated_at=fetched_at,
            return_on_invested_capital=(
                return_on_invested_capital
            ),
            **values,
        )

        quality = FundamentalDataQualityService.evaluate(
            snapshot=snapshot,
            source="Yahoo Finance",
            fetched_at=fetched_at,
        )

        return replace(
            snapshot,
            data_quality=quality,
        )

    @classmethod
    def _calculate_roic(
        cls,
        raw_info: dict[str, Any],
    ) -> float | None:
        """
        Estimate ROIC when the required provider fields exist.

        ROIC = operating income after tax / invested capital.
        """
        operating_income = cls._optional_number(
            raw_info.get("operatingIncome")
        )
        tax_rate = cls._optional_number(
            raw_info.get("effectiveTaxRate")
        )
        total_debt = cls._optional_number(
            raw_info.get("totalDebt")
        )
        stockholder_equity = cls._optional_number(
            raw_info.get("totalStockholderEquity")
        )
        total_cash = cls._optional_number(
            raw_info.get("totalCash")
        )

        required_values = (
            operating_income,
            tax_rate,
            total_debt,
            stockholder_equity,
            total_cash,
        )

        if any(
            value is None
            for value in required_values
        ):
            return None

        invested_capital = (
            total_debt
            + stockholder_equity
            - total_cash
        )

        if invested_capital <= 0:
            return None

        after_tax_operating_income = (
            operating_income
            * (1.0 - tax_rate)
        )

        return (
            after_tax_operating_income
            / invested_capital
        )

    @staticmethod
    def _optional_number(
        value: object,
    ) -> float | None:
        """
        Convert a provider value to a finite float or None.
        """
        if value is None:
            return None

        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            return None

        return float(value)

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip().upper()
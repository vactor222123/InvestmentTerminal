"""
Normalized fundamental-data models.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from numbers import Real
from typing import Any


@dataclass(frozen=True, slots=True)
class FundamentalDataQuality:
    """
    Quality and completeness metadata for fundamental data.
    """

    available_fields: int
    total_fields: int
    completeness_percent: float
    missing_fields: tuple[str, ...]
    source: str
    fetched_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the model to a JSON-ready dictionary.
        """
        result = asdict(self)
        result["missing_fields"] = list(self.missing_fields)
        result["fetched_at"] = self.fetched_at.isoformat()

        return result


@dataclass(frozen=True, slots=True)
class FundamentalSnapshot:
    """
    Normalized fundamental snapshot for one asset.

    Percentage and ratio values use decimal form:
    0.15 means 15 percent.
    """

    symbol: str
    currency: str
    generated_at: datetime

    market_cap: float | None = None
    enterprise_value: float | None = None

    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    enterprise_to_ebitda: float | None = None

    revenue: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    eps_trailing: float | None = None
    eps_forward: float | None = None

    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None

    return_on_equity: float | None = None
    return_on_assets: float | None = None
    return_on_invested_capital: float | None = None

    total_cash: float | None = None
    total_debt: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None

    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None

    dividend_yield: float | None = None
    payout_ratio: float | None = None

    data_quality: FundamentalDataQuality | None = None

    def __post_init__(self) -> None:
        """
        Validate normalized fundamental data.
        """
        normalized_symbol = self.symbol.strip().upper()
        normalized_currency = self.currency.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol must be a non-empty string")

        if not normalized_currency:
            raise ValueError("currency must be a non-empty string")

        if not isinstance(self.generated_at, datetime):
            raise TypeError("generated_at must be a datetime")

        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )
        object.__setattr__(
            self,
            "currency",
            normalized_currency,
        )

        for field_name in self.metric_field_names():
            value = getattr(self, field_name)

            if value is None:
                continue

            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not isfinite(float(value))
            ):
                raise ValueError(
                    f"{field_name} must be a finite number or None"
                )

    @classmethod
    def metric_field_names(cls) -> tuple[str, ...]:
        """
        Return fields used when calculating completeness.
        """
        return (
            "market_cap",
            "enterprise_value",
            "trailing_pe",
            "forward_pe",
            "peg_ratio",
            "price_to_book",
            "price_to_sales",
            "enterprise_to_ebitda",
            "revenue",
            "revenue_growth",
            "earnings_growth",
            "eps_trailing",
            "eps_forward",
            "gross_margin",
            "operating_margin",
            "net_margin",
            "return_on_equity",
            "return_on_assets",
            "return_on_invested_capital",
            "total_cash",
            "total_debt",
            "debt_to_equity",
            "current_ratio",
            "quick_ratio",
            "operating_cash_flow",
            "free_cash_flow",
            "dividend_yield",
            "payout_ratio",
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the snapshot into a JSON-ready dictionary.
        """
        result = asdict(self)
        result["generated_at"] = self.generated_at.isoformat()

        if self.data_quality is not None:
            result["data_quality"] = (
                self.data_quality.to_dict()
            )

        return result
"""
Pure descriptive calculator for one historical recommendation price outcome.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Any

from investment_terminal.history.historical_outcome_models import (
    HistoricalOutcomeEvidence,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalRecommendationOutcome:
    """
    Descriptive raw price movement for one complete historical evidence pair.

    This model does not encode investment success, portfolio performance,
    annualization, action-direction interpretation, or causality.
    """

    instrument_key: str
    currency: str
    origin_price: float
    endpoint_price: float
    price_change: float
    price_change_fraction: float
    origin_source: str
    endpoint_source: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instrument_key",
            normalize_required_text(
                self.instrument_key,
                field_name="instrument_key",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_required_text(
                self.currency,
                field_name="currency",
                uppercase=True,
            ),
        )

        for field_name in (
            "origin_price",
            "endpoint_price",
            "price_change",
            "price_change_fraction",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                isinstance(value, bool)
                or not isinstance(
                    value,
                    (int, float),
                )
                or not isfinite(
                    float(value)
                )
            ):
                raise ValueError(
                    f"{field_name} must be a finite number"
                )
            object.__setattr__(
                self,
                field_name,
                float(value),
            )

        if self.origin_price <= 0.0:
            raise ValueError(
                "origin_price must be greater than zero"
            )
        if self.endpoint_price <= 0.0:
            raise ValueError(
                "endpoint_price must be greater than zero"
            )

        object.__setattr__(
            self,
            "origin_source",
            normalize_required_text(
                self.origin_source,
                field_name="origin_source",
            ),
        )
        object.__setattr__(
            self,
            "endpoint_source",
            normalize_required_text(
                self.endpoint_source,
                field_name="endpoint_source",
            ),
        )

        expected_change = (
            self.endpoint_price
            - self.origin_price
        )
        expected_fraction = (
            self.endpoint_price
            / self.origin_price
        ) - 1.0

        if self.price_change != expected_change:
            raise ValueError(
                "price_change must match endpoint_price - origin_price"
            )
        if self.price_change_fraction != expected_fraction:
            raise ValueError(
                "price_change_fraction must match "
                "(endpoint_price / origin_price) - 1"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "currency": self.currency,
            "origin_price": self.origin_price,
            "endpoint_price": self.endpoint_price,
            "price_change": self.price_change,
            "price_change_fraction": self.price_change_fraction,
            "origin_source": self.origin_source,
            "endpoint_source": self.endpoint_source,
        }


class HistoricalRecommendationOutcomeCalculator:
    """
    Calculate one transparent raw price movement from complete evidence.

    The calculator is pure: no repositories, clocks, network access, action
    interpretation, performance attribution, or nearest-date logic.
    """

    def calculate(
        self,
        *,
        evidence: HistoricalOutcomeEvidence,
        origin_currency: str,
        endpoint_currency: str,
    ) -> HistoricalRecommendationOutcome:
        if not isinstance(
            evidence,
            HistoricalOutcomeEvidence,
        ):
            raise TypeError(
                "evidence must be a HistoricalOutcomeEvidence"
            )

        if not evidence.has_complete_prices:
            raise ValueError(
                "complete origin and endpoint prices are required"
            )

        if evidence.origin_source is None:
            raise ValueError(
                "origin_source is required"
            )
        if evidence.endpoint_source is None:
            raise ValueError(
                "endpoint_source is required"
            )

        normalized_origin_currency = normalize_required_text(
            origin_currency,
            field_name="origin_currency",
            uppercase=True,
        )
        normalized_endpoint_currency = normalize_required_text(
            endpoint_currency,
            field_name="endpoint_currency",
            uppercase=True,
        )

        if normalized_origin_currency != normalized_endpoint_currency:
            raise ValueError(
                "origin and endpoint currency must match; "
                "FX-adjusted outcome calculation is not supported"
            )

        assert evidence.origin_price is not None
        assert evidence.endpoint_price is not None

        origin_price = float(
            evidence.origin_price
        )
        endpoint_price = float(
            evidence.endpoint_price
        )

        return HistoricalRecommendationOutcome(
            instrument_key=evidence.instrument_key,
            currency=normalized_origin_currency,
            origin_price=origin_price,
            endpoint_price=endpoint_price,
            price_change=(
                endpoint_price
                - origin_price
            ),
            price_change_fraction=(
                endpoint_price
                / origin_price
            )
            - 1.0,
            origin_source=evidence.origin_source,
            endpoint_source=evidence.endpoint_source,
        )

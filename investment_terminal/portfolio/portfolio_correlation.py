"""Deterministic pairwise correlation evidence for portfolio return inputs."""

from dataclasses import dataclass
from datetime import datetime
from math import isclose, sqrt
from typing import Any

from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    RETURN_SERIES_SUBJECT_TYPES,
    ReturnSeries,
    RiskDataProvenance,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)

CORRELATION_UNAVAILABLE_REASONS = (
    "CURRENCY_MISMATCH",
    "PERIOD_MISMATCH",
    "INSUFFICIENT_OVERLAP",
    "ZERO_VARIANCE",
)


@dataclass(frozen=True, slots=True)
class PortfolioCorrelationPair:
    """Correlation evidence for one deterministically ordered subject pair."""

    left_subject_type: str
    left_subject_key: str
    right_subject_type: str
    right_subject_key: str
    observation_count: int
    coefficient: float | None
    unavailable_reason: str | None
    left_provenance: RiskDataProvenance
    right_provenance: RiskDataProvenance

    def __post_init__(self) -> None:
        for field_name in (
            "left_subject_type",
            "left_subject_key",
            "right_subject_type",
            "right_subject_key",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name, uppercase=True
                ),
            )
        if self.left_subject_type not in RETURN_SERIES_SUBJECT_TYPES:
            raise ValueError("left_subject_type is not supported")
        if self.right_subject_type not in RETURN_SERIES_SUBJECT_TYPES:
            raise ValueError("right_subject_type is not supported")
        if (
            isinstance(self.observation_count, bool)
            or not isinstance(self.observation_count, int)
            or self.observation_count < 0
        ):
            raise ValueError("observation_count must be a non-negative integer")
        if self.coefficient is None:
            reason = normalize_required_text(
                self.unavailable_reason, field_name="unavailable_reason", uppercase=True
            )
            if reason not in CORRELATION_UNAVAILABLE_REASONS:
                raise ValueError("unavailable_reason is not supported")
            object.__setattr__(self, "unavailable_reason", reason)
        else:
            coefficient = validate_finite_number(
                self.coefficient, field_name="coefficient"
            )
            if not -1 <= coefficient <= 1:
                raise ValueError("coefficient must be between -1 and 1")
            if self.observation_count < 2:
                raise ValueError(
                    "available correlation requires at least two observations"
                )
            if self.unavailable_reason is not None:
                raise ValueError(
                    "available correlation must not have unavailable_reason"
                )
            object.__setattr__(self, "coefficient", coefficient)
        for field_name in ("left_provenance", "right_provenance"):
            if not isinstance(getattr(self, field_name), RiskDataProvenance):
                raise TypeError(f"{field_name} must be a RiskDataProvenance")

    @property
    def available(self) -> bool:
        return self.coefficient is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_subject_type": self.left_subject_type,
            "left_subject_key": self.left_subject_key,
            "right_subject_type": self.right_subject_type,
            "right_subject_key": self.right_subject_key,
            "observation_count": self.observation_count,
            "coefficient": self.coefficient,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "left_provenance": self.left_provenance.to_dict(),
            "right_provenance": self.right_provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PortfolioCorrelationAnalysis:
    """Immutable pairwise correlation evidence at one portfolio cutoff."""

    ledger_id: str
    portfolio_name: str
    as_of: datetime
    pairs: tuple[PortfolioCorrelationPair, ...]

    def __post_init__(self) -> None:
        for field_name in ("ledger_id", "portfolio_name"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        validate_aware_datetime(self.as_of, field_name="as_of")
        if not isinstance(self.pairs, tuple):
            raise TypeError("pairs must be a tuple")
        if any(not isinstance(item, PortfolioCorrelationPair) for item in self.pairs):
            raise TypeError("pairs must contain only PortfolioCorrelationPair objects")
        keys = tuple(
            (
                item.left_subject_type,
                item.left_subject_key,
                item.right_subject_type,
                item.right_subject_key,
            )
            for item in self.pairs
        )
        if keys != tuple(sorted(keys)):
            raise ValueError("pairs must be deterministically ordered")
        if len(keys) != len(set(keys)):
            raise ValueError("pairs must be unique")
        if any(
            provenance.fetched_at > self.as_of
            for item in self.pairs
            for provenance in (item.left_provenance, item.right_provenance)
        ):
            raise ValueError("pair provenance must not be later than as_of")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "as_of": self.as_of.isoformat(),
            "pair_count": len(self.pairs),
            "available_pair_count": sum(item.available for item in self.pairs),
            "pairs": [item.to_dict() for item in self.pairs],
        }


class PortfolioCorrelationCalculator:
    """Calculate pairwise Pearson correlation without causal interpretation."""

    @staticmethod
    def calculate(risk_input: PortfolioRiskInput) -> PortfolioCorrelationAnalysis:
        if not isinstance(risk_input, PortfolioRiskInput):
            raise TypeError("risk_input must be a PortfolioRiskInput")
        series = (risk_input.portfolio_returns, *risk_input.instrument_returns)
        pairs = tuple(
            PortfolioCorrelationCalculator._calculate_pair(left, right)
            for left_index, left in enumerate(series)
            for right in series[left_index + 1 :]
        )
        return PortfolioCorrelationAnalysis(
            ledger_id=risk_input.ledger_id,
            portfolio_name=risk_input.portfolio_name,
            as_of=risk_input.as_of,
            pairs=tuple(
                sorted(
                    pairs,
                    key=lambda item: (
                        item.left_subject_type,
                        item.left_subject_key,
                        item.right_subject_type,
                        item.right_subject_key,
                    ),
                )
            ),
        )

    @staticmethod
    def _calculate_pair(
        left: ReturnSeries, right: ReturnSeries
    ) -> PortfolioCorrelationPair:
        if left.currency != right.currency:
            return PortfolioCorrelationCalculator._unavailable(
                left, right, 0, "CURRENCY_MISMATCH"
            )
        if left.period != right.period:
            return PortfolioCorrelationCalculator._unavailable(
                left, right, 0, "PERIOD_MISMATCH"
            )
        right_values = {
            item.period_key: item.return_fraction for item in right.observations
        }
        aligned = tuple(
            (item.return_fraction, right_values[item.period_key])
            for item in left.observations
            if item.period_key in right_values
        )
        if len(aligned) < 2:
            return PortfolioCorrelationCalculator._unavailable(
                left, right, len(aligned), "INSUFFICIENT_OVERLAP"
            )
        left_mean = sum(item[0] for item in aligned) / len(aligned)
        right_mean = sum(item[1] for item in aligned) / len(aligned)
        covariance_sum = sum(
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in aligned
        )
        left_square_sum = sum((item[0] - left_mean) ** 2 for item in aligned)
        right_square_sum = sum((item[1] - right_mean) ** 2 for item in aligned)
        if left_square_sum == 0 or right_square_sum == 0:
            return PortfolioCorrelationCalculator._unavailable(
                left, right, len(aligned), "ZERO_VARIANCE"
            )
        coefficient = covariance_sum / sqrt(left_square_sum * right_square_sum)
        if isclose(abs(coefficient), 1.0, rel_tol=0, abs_tol=1e-12):
            coefficient = 1.0 if coefficient > 0 else -1.0
        return PortfolioCorrelationPair(
            left.subject_type,
            left.subject_key,
            right.subject_type,
            right.subject_key,
            len(aligned),
            coefficient,
            None,
            left.provenance,
            right.provenance,
        )

    @staticmethod
    def _unavailable(
        left: ReturnSeries, right: ReturnSeries, count: int, reason: str
    ) -> PortfolioCorrelationPair:
        return PortfolioCorrelationPair(
            left.subject_type,
            left.subject_key,
            right.subject_type,
            right.subject_key,
            count,
            None,
            reason,
            left.provenance,
            right.provenance,
        )

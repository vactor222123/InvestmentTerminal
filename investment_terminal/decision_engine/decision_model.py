"""
Structured investment decision models.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from numbers import Real
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_score_0_100,
)


@dataclass(frozen=True, slots=True)
class DecisionScoreSummary:
    """
    Scores contributing to the combined decision.
    """

    technical: float
    fundamental: float
    overall: float

    technical_weight: float
    fundamental_weight: float

    def __post_init__(self) -> None:
        for field_name in (
            "technical",
            "fundamental",
            "overall",
        ):
            validate_score_0_100(
                getattr(self, field_name),
                field_name=field_name,
            )

        for field_name in (
            "technical_weight",
            "fundamental_weight",
        ):
            value = getattr(self, field_name)
            _validate_weight(
                value=value,
                field_name=field_name,
            )

        weight_total = (
            self.technical_weight
            + self.fundamental_weight
        )

        if abs(weight_total - 1.0) > 0.0001:
            raise ValueError(
                "Decision weights must sum to 1.0"
            )

    def to_dict(self) -> dict[str, float]:
        """
        Convert the score summary to a JSON-ready dictionary.
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DecisionQualitySummary:
    """
    Descriptive assessment of the analyzed business.
    """

    business_quality: str
    financial_health: str
    growth: str
    valuation: str
    technical_condition: str
    risk_level: str

    def __post_init__(self) -> None:
        for field_name in (
            "business_quality",
            "financial_health",
            "growth",
            "valuation",
            "technical_condition",
            "risk_level",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                    uppercase=True,
                ),
            )

    def to_dict(self) -> dict[str, str]:
        """
        Convert the quality summary to a dictionary.
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DecisionConfidence:
    """
    Confidence in the generated decision.
    """

    score: float
    classification: str
    technical_data_quality: float
    fundamental_data_quality: float
    missing_data_penalty: float

    def __post_init__(self) -> None:
        for field_name in (
            "score",
            "technical_data_quality",
            "fundamental_data_quality",
        ):
            validate_score_0_100(
                getattr(self, field_name),
                field_name=field_name,
            )

        validate_score_0_100(
            self.missing_data_penalty,
            field_name="missing_data_penalty",
        )

        object.__setattr__(
            self,
            "classification",
            normalize_required_text(
                self.classification,
                field_name="classification",
                uppercase=True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert confidence metadata to a dictionary.
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """
    Final structured result produced by the Decision Engine.

    This model contains analytical context only. It does not represent
    personalized financial advice or an automatic trading instruction.
    """

    schema_version: str
    generated_at: datetime

    symbol: str
    currency: str

    scores: DecisionScoreSummary
    quality: DecisionQualitySummary
    confidence: DecisionConfidence

    classification: str
    positive_factors: tuple[str, ...]
    risk_factors: tuple[str, ...]
    missing_data: tuple[str, ...]

    summary: str

    def __post_init__(self) -> None:
        normalized_schema_version = normalize_required_text(
            self.schema_version,
            field_name="schema_version",
        )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        normalized_symbol = normalize_required_text(
            self.symbol,
            field_name="symbol",
            uppercase=True,
        )
        normalized_currency = normalize_required_text(
            self.currency,
            field_name="currency",
            uppercase=True,
        )
        normalized_classification = normalize_required_text(
            self.classification,
            field_name="classification",
            uppercase=True,
        )
        normalized_summary = normalize_required_text(
            self.summary,
            field_name="summary",
        )

        for collection_name in (
            "positive_factors",
            "risk_factors",
            "missing_data",
        ):
            values = getattr(
                self,
                collection_name,
            )

            if not isinstance(values, tuple):
                raise TypeError(
                    f"{collection_name} must be a tuple"
                )

            if any(
                not isinstance(value, str)
                or not value.strip()
                for value in values
            ):
                raise ValueError(
                    f"{collection_name} must contain "
                    "only non-empty strings"
                )

        object.__setattr__(
            self,
            "schema_version",
            normalized_schema_version,
        )
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
        object.__setattr__(
            self,
            "classification",
            normalized_classification,
        )
        object.__setattr__(
            self,
            "summary",
            normalized_summary,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the complete result to a JSON-ready dictionary.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "symbol": self.symbol,
            "currency": self.currency,
            "scores": self.scores.to_dict(),
            "quality": self.quality.to_dict(),
            "confidence": self.confidence.to_dict(),
            "classification": self.classification,
            "positive_factors": list(
                self.positive_factors
            ),
            "risk_factors": list(
                self.risk_factors
            ),
            "missing_data": list(
                self.missing_data
            ),
            "summary": self.summary,
        }


def _validate_weight(
    value: object,
    field_name: str,
) -> None:
    """
    Validate a normalized weight.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(float(value))
    ):
        raise ValueError(
            f"{field_name} must be a finite number"
        )

    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(
            f"{field_name} must be between 0 and 1"
        )

"""
Structured investment decision models.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite
from numbers import Real
from typing import Any


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
            value = getattr(self, field_name)
            _validate_score(
                value=value,
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
            value = getattr(self, field_name)

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be "
                    "a non-empty string"
                )

            object.__setattr__(
                self,
                field_name,
                value.strip().upper(),
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
            value = getattr(self, field_name)
            _validate_score(
                value=value,
                field_name=field_name,
            )

        _validate_score(
            value=self.missing_data_penalty,
            field_name="missing_data_penalty",
        )

        if (
            not isinstance(self.classification, str)
            or not self.classification.strip()
        ):
            raise ValueError(
                "classification must be "
                "a non-empty string"
            )

        object.__setattr__(
            self,
            "classification",
            self.classification.strip().upper(),
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
        if (
            not isinstance(self.schema_version, str)
            or not self.schema_version.strip()
        ):
            raise ValueError(
                "schema_version must be "
                "a non-empty string"
            )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        normalized_symbol = _normalize_text(
            self.symbol,
            field_name="symbol",
        )
        normalized_currency = _normalize_text(
            self.currency,
            field_name="currency",
        )
        normalized_classification = _normalize_text(
            self.classification,
            field_name="classification",
        )

        if (
            not isinstance(self.summary, str)
            or not self.summary.strip()
        ):
            raise ValueError(
                "summary must be a non-empty string"
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
            self.schema_version.strip(),
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
            self.summary.strip(),
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


def _validate_score(
    value: object,
    field_name: str,
) -> None:
    """
    Validate a score expressed on a 0–100 scale.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(float(value))
    ):
        raise ValueError(
            f"{field_name} must be a finite number"
        )

    if not 0.0 <= float(value) <= 100.0:
        raise ValueError(
            f"{field_name} must be between 0 and 100"
        )


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


def _normalize_text(
    value: str,
    field_name: str,
) -> str:
    """
    Normalize required textual fields.
    """
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    return value.strip().upper()
"""
Canonical immutable contracts for outcome-aware Historical Intelligence.
"""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, ClassVar

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
)


def _normalize_optional_price(
    value: object,
    *,
    field_name: str,
) -> float | None:
    if value is None:
        return None

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (
                int,
                float,
            ),
        )
        or not isfinite(
            float(
                value
            )
        )
        or float(
            value
        )
        <= 0.0
    ):
        raise ValueError(
            f"{field_name} must be a finite positive number or None"
        )

    return float(
        value
    )


@dataclass(frozen=True, slots=True)
class HistoricalObservationWindow:
    """
    Explicit outcome observation-window request.

    Endpoint calculation belongs to the observation-window policy, not this
    value object.
    """

    kind: str
    value: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "kind",
            normalize_required_text(
                self.kind,
                field_name="kind",
                uppercase=True,
            ),
        )

        if (
            not isinstance(
                self.value,
                int,
            )
            or isinstance(
                self.value,
                bool,
            )
            or self.value
            <= 0
        ):
            raise ValueError(
                "value must be a positive integer"
            )

    def to_dict(
        self,
    ) -> dict[str, str | int]:
        return {
            "kind": self.kind,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeEvidence:
    """
    Explicit price evidence used by one historical outcome observation.

    The model records facts and provenance only. It does not calculate returns,
    infer missing prices, or fetch external data.
    """

    instrument_key: str
    origin_at: datetime
    endpoint_at: datetime | None
    origin_price: float | None
    endpoint_price: float | None
    origin_source: str | None
    endpoint_source: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instrument_key",
            normalize_required_text(
                self.instrument_key,
                field_name="instrument_key",
            ),
        )

        validate_aware_datetime(
            self.origin_at,
            field_name="origin_at",
        )

        if self.endpoint_at is not None:
            validate_aware_datetime(
                self.endpoint_at,
                field_name="endpoint_at",
            )

            if self.endpoint_at < self.origin_at:
                raise ValueError(
                    "endpoint_at must not be earlier than origin_at"
                )

        object.__setattr__(
            self,
            "origin_price",
            _normalize_optional_price(
                self.origin_price,
                field_name="origin_price",
            ),
        )
        object.__setattr__(
            self,
            "endpoint_price",
            _normalize_optional_price(
                self.endpoint_price,
                field_name="endpoint_price",
            ),
        )
        object.__setattr__(
            self,
            "origin_source",
            normalize_optional_text(
                self.origin_source,
                field_name="origin_source",
            ),
        )
        object.__setattr__(
            self,
            "endpoint_source",
            normalize_optional_text(
                self.endpoint_source,
                field_name="endpoint_source",
            ),
        )

        if (
            self.origin_price is not None
            and self.origin_source is None
        ):
            raise ValueError(
                "origin_source is required when origin_price is present"
            )

        if (
            self.endpoint_price is not None
            and self.endpoint_at is None
        ):
            raise ValueError(
                "endpoint_at is required when endpoint_price is present"
            )

        if (
            self.endpoint_price is not None
            and self.endpoint_source is None
        ):
            raise ValueError(
                "endpoint_source is required when endpoint_price is present"
            )

    @property
    def has_complete_prices(
        self,
    ) -> bool:
        return (
            self.origin_price is not None
            and self.endpoint_price is not None
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "origin_at": self.origin_at.isoformat(),
            "endpoint_at": (
                None
                if self.endpoint_at is None
                else self.endpoint_at.isoformat()
            ),
            "origin_price": self.origin_price,
            "endpoint_price": self.endpoint_price,
            "origin_source": self.origin_source,
            "endpoint_source": self.endpoint_source,
            "complete_prices": self.has_complete_prices,
        }


@dataclass(frozen=True, slots=True)
class HistoricalRecommendationObservation:
    """
    One descriptive observation request/result envelope for a recommendation.

    `status` describes evidence maturity/completeness. No success/failure or
    causal interpretation is encoded by this model.
    """

    origin_snapshot_id: str
    recommendation_key: str
    symbol: str | None
    action: str | None
    origin_at: datetime
    window: HistoricalObservationWindow
    status: str
    evidence: HistoricalOutcomeEvidence | None = None
    warnings: tuple[str, ...] = ()

    COMPLETE: ClassVar[str] = "COMPLETE"
    PARTIAL: ClassVar[str] = "PARTIAL"
    UNAVAILABLE: ClassVar[str] = "UNAVAILABLE"
    NOT_MATURE: ClassVar[str] = "NOT_MATURE"

    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = (
        COMPLETE,
        PARTIAL,
        UNAVAILABLE,
        NOT_MATURE,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "origin_snapshot_id",
            HistoricalSnapshot._normalize_uuid(
                self.origin_snapshot_id,
                field_name="origin_snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "recommendation_key",
            normalize_required_text(
                self.recommendation_key,
                field_name="recommendation_key",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            normalize_optional_text(
                self.symbol,
                field_name="symbol",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "action",
            normalize_optional_text(
                self.action,
                field_name="action",
                uppercase=True,
            ),
        )

        validate_aware_datetime(
            self.origin_at,
            field_name="origin_at",
        )

        if not isinstance(
            self.window,
            HistoricalObservationWindow,
        ):
            raise TypeError(
                "window must be a HistoricalObservationWindow"
            )

        normalized_status = normalize_required_text(
            self.status,
            field_name="status",
            uppercase=True,
        )

        if normalized_status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(
                    self.SUPPORTED_STATUSES
                )
            )

        object.__setattr__(
            self,
            "status",
            normalized_status,
        )

        if (
            self.evidence is not None
            and not isinstance(
                self.evidence,
                HistoricalOutcomeEvidence,
            )
        ):
            raise TypeError(
                "evidence must be a HistoricalOutcomeEvidence or None"
            )

        if (
            self.evidence is not None
            and self.evidence.origin_at
            != self.origin_at
        ):
            raise ValueError(
                "evidence origin_at must match observation origin_at"
            )

        if (
            self.status == self.COMPLETE
            and (
                self.evidence is None
                or not self.evidence.has_complete_prices
            )
        ):
            raise ValueError(
                "COMPLETE observation requires complete origin and endpoint prices"
            )

        if (
            self.status == self.NOT_MATURE
            and self.evidence is not None
            and self.evidence.endpoint_price is not None
        ):
            raise ValueError(
                "NOT_MATURE observation must not contain endpoint_price"
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        object.__setattr__(
            self,
            "warnings",
            tuple(
                normalize_required_text(
                    warning,
                    field_name="warning",
                )
                for warning in self.warnings
            ),
        )

    @property
    def has_complete_outcome_evidence(
        self,
    ) -> bool:
        return (
            self.status == self.COMPLETE
            and self.evidence is not None
            and self.evidence.has_complete_prices
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "origin_snapshot_id": self.origin_snapshot_id,
            "recommendation_key": self.recommendation_key,
            "symbol": self.symbol,
            "action": self.action,
            "origin_at": self.origin_at.isoformat(),
            "window": self.window.to_dict(),
            "status": self.status,
            "evidence": (
                None
                if self.evidence is None
                else self.evidence.to_dict()
            ),
            "warnings": list(
                self.warnings
            ),
            "complete_outcome_evidence": (
                self.has_complete_outcome_evidence
            ),
        }

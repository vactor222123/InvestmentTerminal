"""
Canonical immutable models for historical snapshot comparison results.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class ScalarChange:
    """Serializable previous/current scalar comparison with safe deltas."""

    previous: float | int | None
    current: float | int | None
    absolute_change: float | None = None
    percentage_change: float | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "previous",
            "current",
            "absolute_change",
            "percentage_change",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                value is not None
                and (
                    not isinstance(
                        value,
                        (
                            int,
                            float,
                        ),
                    )
                    or isinstance(
                        value,
                        bool,
                    )
                )
            ):
                raise TypeError(
                    f"{field_name} must be numeric or None"
                )

        if self.absolute_change is not None:
            if self.previous is None or self.current is None:
                raise ValueError(
                    "absolute_change requires previous and current values"
                )

        if self.percentage_change is not None:
            if (
                self.previous is None
                or self.current is None
            ):
                raise ValueError(
                    "percentage_change requires previous and current values"
                )

            if float(
                self.previous
            ) == 0.0:
                raise ValueError(
                    "percentage_change is undefined when previous is zero"
                )

    @classmethod
    def between(
        cls,
        previous: float | int | None,
        current: float | int | None,
        *,
        include_percentage: bool = True,
    ) -> "ScalarChange":
        """Build a change without inventing deltas for absent values."""
        if previous is None or current is None:
            return cls(
                previous=previous,
                current=current,
            )

        absolute = float(
            current
        ) - float(
            previous
        )

        percentage = None
        if (
            include_percentage
            and float(
                previous
            ) != 0.0
        ):
            percentage = (
                absolute
                / abs(
                    float(
                        previous
                    )
                )
            ) * 100.0

        return cls(
            previous=previous,
            current=current,
            absolute_change=absolute,
            percentage_change=percentage,
        )

    def to_dict(
        self,
    ) -> dict[str, float | int | None]:
        return {
            "previous": self.previous,
            "current": self.current,
            "absolute_change": self.absolute_change,
            "percentage_change": self.percentage_change,
        }


@dataclass(frozen=True, slots=True)
class PortfolioSummaryChange:
    """Comparison of normalized portfolio-summary values."""

    previous_exists: bool
    current_exists: bool
    base_currency_previous: str | None
    base_currency_current: str | None
    source_status_previous: str | None
    source_status_current: str | None
    total_value: ScalarChange
    invested_value: ScalarChange
    cash_value: ScalarChange
    monthly_contribution: ScalarChange
    cash_weight: ScalarChange
    invested_weight: ScalarChange

    def __post_init__(self) -> None:
        for field_name in (
            "previous_exists",
            "current_exists",
        ):
            if not isinstance(
                getattr(
                    self,
                    field_name,
                ),
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a boolean"
                )

        for field_name in (
            "base_currency_previous",
            "base_currency_current",
            "source_status_previous",
            "source_status_current",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_optional_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name=field_name,
                ),
            )

        for field_name in (
            "total_value",
            "invested_value",
            "cash_value",
            "monthly_contribution",
            "cash_weight",
            "invested_weight",
        ):
            if not isinstance(
                getattr(
                    self,
                    field_name,
                ),
                ScalarChange,
            ):
                raise TypeError(
                    f"{field_name} must be a ScalarChange"
                )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "previous_exists": self.previous_exists,
            "current_exists": self.current_exists,
            "base_currency_previous": self.base_currency_previous,
            "base_currency_current": self.base_currency_current,
            "source_status_previous": self.source_status_previous,
            "source_status_current": self.source_status_current,
            "total_value": self.total_value.to_dict(),
            "invested_value": self.invested_value.to_dict(),
            "cash_value": self.cash_value.to_dict(),
            "monthly_contribution": self.monthly_contribution.to_dict(),
            "cash_weight": self.cash_weight.to_dict(),
            "invested_weight": self.invested_weight.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class HoldingChange:
    """Comparison result for one stable historical holding key."""

    holding_key: str
    change_type: str
    previous: dict[str, Any] | None
    current: dict[str, Any] | None
    quantity: ScalarChange
    unit_price: ScalarChange
    market_value: ScalarChange
    weight: ScalarChange

    SUPPORTED_CHANGE_TYPES: ClassVar[tuple[str, ...]] = (
        "ADDED",
        "REMOVED",
        "CHANGED",
        "UNCHANGED",
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "holding_key",
            normalize_required_text(
                self.holding_key,
                field_name="holding_key",
            ),
        )
        object.__setattr__(
            self,
            "change_type",
            _normalize_change_type(
                self.change_type,
                supported=self.SUPPORTED_CHANGE_TYPES,
            ),
        )
        _validate_optional_payload(
            self.previous,
            field_name="previous",
        )
        _validate_optional_payload(
            self.current,
            field_name="current",
        )
        _validate_presence_contract(
            self.change_type,
            previous=self.previous,
            current=self.current,
        )
        _validate_scalar_fields(
            self,
            (
                "quantity",
                "unit_price",
                "market_value",
                "weight",
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "holding_key": self.holding_key,
            "change_type": self.change_type,
            "previous": self.previous,
            "current": self.current,
            "quantity": self.quantity.to_dict(),
            "unit_price": self.unit_price.to_dict(),
            "market_value": self.market_value.to_dict(),
            "weight": self.weight.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RecommendationChange:
    """Comparison result for one historical recommendation key."""

    recommendation_key: str
    change_type: str
    previous: dict[str, Any] | None
    current: dict[str, Any] | None
    score: ScalarChange
    confidence: ScalarChange

    SUPPORTED_CHANGE_TYPES: ClassVar[tuple[str, ...]] = (
        "ADDED",
        "REMOVED",
        "CHANGED",
        "UNCHANGED",
    )

    def __post_init__(self) -> None:
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
            "change_type",
            _normalize_change_type(
                self.change_type,
                supported=self.SUPPORTED_CHANGE_TYPES,
            ),
        )
        _validate_optional_payload(
            self.previous,
            field_name="previous",
        )
        _validate_optional_payload(
            self.current,
            field_name="current",
        )
        _validate_presence_contract(
            self.change_type,
            previous=self.previous,
            current=self.current,
        )
        _validate_scalar_fields(
            self,
            (
                "score",
                "confidence",
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "recommendation_key": self.recommendation_key,
            "change_type": self.change_type,
            "previous": self.previous,
            "current": self.current,
            "score": self.score.to_dict(),
            "confidence": self.confidence.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DeploymentChange:
    """Comparison result for one historical deployment key."""

    deployment_key: str
    change_type: str
    previous: dict[str, Any] | None
    current: dict[str, Any] | None
    amount: ScalarChange
    share: ScalarChange

    SUPPORTED_CHANGE_TYPES: ClassVar[tuple[str, ...]] = (
        "ADDED",
        "REMOVED",
        "CHANGED",
        "UNCHANGED",
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "deployment_key",
            normalize_required_text(
                self.deployment_key,
                field_name="deployment_key",
            ),
        )
        object.__setattr__(
            self,
            "change_type",
            _normalize_change_type(
                self.change_type,
                supported=self.SUPPORTED_CHANGE_TYPES,
            ),
        )
        _validate_optional_payload(
            self.previous,
            field_name="previous",
        )
        _validate_optional_payload(
            self.current,
            field_name="current",
        )
        _validate_presence_contract(
            self.change_type,
            previous=self.previous,
            current=self.current,
        )
        _validate_scalar_fields(
            self,
            (
                "amount",
                "share",
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "deployment_key": self.deployment_key,
            "change_type": self.change_type,
            "previous": self.previous,
            "current": self.current,
            "amount": self.amount.to_dict(),
            "share": self.share.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SnapshotComparison:
    """Canonical aggregate comparison between two historical snapshots."""

    earlier_snapshot_id: str
    later_snapshot_id: str
    compatibility_status: str
    portfolio_summary: PortfolioSummaryChange | None
    holdings: tuple[HoldingChange, ...]
    recommendations: tuple[RecommendationChange, ...]
    deployment: tuple[DeploymentChange, ...]
    compatibility_notes: tuple[str, ...] = ()

    SUPPORTED_COMPATIBILITY_STATUSES: ClassVar[tuple[str, ...]] = (
        "COMPATIBLE",
        "PARTIALLY_COMPATIBLE",
        "INCOMPATIBLE",
    )

    def __post_init__(self) -> None:
        earlier = HistoricalSnapshot._normalize_uuid(
            self.earlier_snapshot_id,
            field_name="earlier_snapshot_id",
        )
        later = HistoricalSnapshot._normalize_uuid(
            self.later_snapshot_id,
            field_name="later_snapshot_id",
        )

        if earlier == later:
            raise ValueError(
                "earlier_snapshot_id and later_snapshot_id must differ"
            )

        object.__setattr__(
            self,
            "earlier_snapshot_id",
            earlier,
        )
        object.__setattr__(
            self,
            "later_snapshot_id",
            later,
        )

        status = normalize_required_text(
            self.compatibility_status,
            field_name="compatibility_status",
            uppercase=True,
        )
        if status not in self.SUPPORTED_COMPATIBILITY_STATUSES:
            raise ValueError(
                "compatibility_status must be one of: "
                + ", ".join(
                    self.SUPPORTED_COMPATIBILITY_STATUSES
                )
            )
        object.__setattr__(
            self,
            "compatibility_status",
            status,
        )

        if (
            self.portfolio_summary is not None
            and not isinstance(
                self.portfolio_summary,
                PortfolioSummaryChange,
            )
        ):
            raise TypeError(
                "portfolio_summary must be a PortfolioSummaryChange or None"
            )

        _validate_tuple_type(
            self.holdings,
            HoldingChange,
            field_name="holdings",
        )
        _validate_tuple_type(
            self.recommendations,
            RecommendationChange,
            field_name="recommendations",
        )
        _validate_tuple_type(
            self.deployment,
            DeploymentChange,
            field_name="deployment",
        )

        if not isinstance(
            self.compatibility_notes,
            tuple,
        ):
            raise TypeError(
                "compatibility_notes must be a tuple"
            )

        normalized_notes = tuple(
            normalize_required_text(
                note,
                field_name="compatibility note",
            )
            for note in self.compatibility_notes
        )
        object.__setattr__(
            self,
            "compatibility_notes",
            normalized_notes,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "earlier_snapshot_id": self.earlier_snapshot_id,
            "later_snapshot_id": self.later_snapshot_id,
            "compatibility_status": self.compatibility_status,
            "compatibility_notes": list(
                self.compatibility_notes
            ),
            "portfolio_summary": (
                None
                if self.portfolio_summary is None
                else self.portfolio_summary.to_dict()
            ),
            "holdings": [
                item.to_dict()
                for item in self.holdings
            ],
            "recommendations": [
                item.to_dict()
                for item in self.recommendations
            ],
            "deployment": [
                item.to_dict()
                for item in self.deployment
            ],
        }


def _normalize_change_type(
    value: object,
    *,
    supported: tuple[str, ...],
) -> str:
    normalized = normalize_required_text(
        value,
        field_name="change_type",
        uppercase=True,
    )

    if normalized not in supported:
        raise ValueError(
            "change_type must be one of: "
            + ", ".join(
                supported
            )
        )

    return normalized


def _validate_optional_payload(
    value: object,
    *,
    field_name: str,
) -> None:
    if value is not None and not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            f"{field_name} must be a dict or None"
        )


def _validate_presence_contract(
    change_type: str,
    *,
    previous: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> None:
    if change_type == "ADDED":
        if previous is not None or current is None:
            raise ValueError(
                "ADDED requires previous=None and current present"
            )
    elif change_type == "REMOVED":
        if previous is None or current is not None:
            raise ValueError(
                "REMOVED requires previous present and current=None"
            )
    else:
        if previous is None or current is None:
            raise ValueError(
                f"{change_type} requires previous and current values"
            )


def _validate_scalar_fields(
    value: object,
    field_names: tuple[str, ...],
) -> None:
    for field_name in field_names:
        if not isinstance(
            getattr(
                value,
                field_name,
            ),
            ScalarChange,
        ):
            raise TypeError(
                f"{field_name} must be a ScalarChange"
            )


def _validate_tuple_type(
    value: object,
    expected_type: type,
    *,
    field_name: str,
) -> None:
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError(
            f"{field_name} must be a tuple"
        )

    if any(
        not isinstance(
            item,
            expected_type,
        )
        for item in value
    ):
        raise TypeError(
            f"{field_name} must contain only {expected_type.__name__} values"
        )

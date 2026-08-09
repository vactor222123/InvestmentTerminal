"""
Canonical immutable research-protocol contracts for historical outcome research.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.utils.validation import (
    normalize_required_text,
)


def _positive_int(
    value: object,
    *,
    field_name: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(
            f"{field_name} must be a positive integer"
        )
    return value


def _normalize_unique_text_tuple(
    value: object,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(
            f"{field_name} must be a tuple"
        )
    if not value:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    normalized = tuple(
        normalize_required_text(
            item,
            field_name=field_name,
            uppercase=True,
        )
        for item in value
    )
    if len(set(normalized)) != len(normalized):
        raise ValueError(
            f"{field_name} must contain unique values"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchProtocol:
    """
    Versioned identity and policy contract for historical outcome research.

    This value object describes how a research sample may be formed and
    reported. It does not select observations, calculate statistics, infer
    recommendation effectiveness, or make predictive/causal claims.
    """

    protocol_id: str
    version: int
    allowed_methodology_identities: tuple[str, ...]
    eligible_statuses: tuple[str, ...]
    minimum_complete_sample_size: int
    grouping_dimensions: tuple[str, ...]
    missing_evidence_policy: str
    uncertainty_policy: str
    claim_policy: str

    DESCRIPTIVE_OUTCOME_RESEARCH: ClassVar[str] = (
        "DESCRIPTIVE_OUTCOME_RESEARCH"
    )
    COMPLETE: ClassVar[str] = "COMPLETE"

    KEEP_VISIBLE: ClassVar[str] = "KEEP_VISIBLE"
    SAMPLE_STANDARD_ERROR: ClassVar[str] = "SAMPLE_STANDARD_ERROR"
    DESCRIPTIVE_ONLY: ClassVar[str] = "DESCRIPTIVE_ONLY"

    METHODOLOGY_IDENTITY: ClassVar[str] = "METHODOLOGY_IDENTITY"
    WINDOW_KIND: ClassVar[str] = "WINDOW_KIND"
    WINDOW_VALUE: ClassVar[str] = "WINDOW_VALUE"
    RECOMMENDATION_KEY: ClassVar[str] = "RECOMMENDATION_KEY"
    SYMBOL: ClassVar[str] = "SYMBOL"
    ACTION: ClassVar[str] = "ACTION"

    REQUIRED_GROUPING_DIMENSIONS: ClassVar[tuple[str, ...]] = (
        METHODOLOGY_IDENTITY,
        WINDOW_KIND,
        WINDOW_VALUE,
    )
    OPTIONAL_GROUPING_DIMENSIONS: ClassVar[tuple[str, ...]] = (
        RECOMMENDATION_KEY,
        SYMBOL,
        ACTION,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "protocol_id",
            normalize_required_text(
                self.protocol_id,
                field_name="protocol_id",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "version",
            _positive_int(
                self.version,
                field_name="version",
            ),
        )
        object.__setattr__(
            self,
            "allowed_methodology_identities",
            _normalize_unique_text_tuple(
                self.allowed_methodology_identities,
                field_name="allowed_methodology_identities",
            ),
        )
        object.__setattr__(
            self,
            "eligible_statuses",
            _normalize_unique_text_tuple(
                self.eligible_statuses,
                field_name="eligible_statuses",
            ),
        )
        object.__setattr__(
            self,
            "minimum_complete_sample_size",
            _positive_int(
                self.minimum_complete_sample_size,
                field_name="minimum_complete_sample_size",
            ),
        )
        object.__setattr__(
            self,
            "grouping_dimensions",
            _normalize_unique_text_tuple(
                self.grouping_dimensions,
                field_name="grouping_dimensions",
            ),
        )
        object.__setattr__(
            self,
            "missing_evidence_policy",
            normalize_required_text(
                self.missing_evidence_policy,
                field_name="missing_evidence_policy",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "uncertainty_policy",
            normalize_required_text(
                self.uncertainty_policy,
                field_name="uncertainty_policy",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "claim_policy",
            normalize_required_text(
                self.claim_policy,
                field_name="claim_policy",
                uppercase=True,
            ),
        )

        unsupported = tuple(
            dimension
            for dimension in self.grouping_dimensions
            if dimension not in (
                self.REQUIRED_GROUPING_DIMENSIONS
                + self.OPTIONAL_GROUPING_DIMENSIONS
            )
        )
        if unsupported:
            raise ValueError(
                "grouping_dimensions contains unsupported values: "
                + ", ".join(unsupported)
            )

        missing_required = tuple(
            dimension
            for dimension in self.REQUIRED_GROUPING_DIMENSIONS
            if dimension not in self.grouping_dimensions
        )
        if missing_required:
            raise ValueError(
                "grouping_dimensions must include: "
                + ", ".join(missing_required)
            )

    @property
    def identity_key(self) -> str:
        return (
            f"{self.protocol_id}"
            f"@{self.version}"
        )

    def allows_methodology(
        self,
        methodology_identity: str,
    ) -> bool:
        normalized = normalize_required_text(
            methodology_identity,
            field_name="methodology_identity",
            uppercase=True,
        )
        return normalized in self.allowed_methodology_identities

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "version": self.version,
            "identity_key": self.identity_key,
            "allowed_methodology_identities": list(
                self.allowed_methodology_identities
            ),
            "eligible_statuses": list(
                self.eligible_statuses
            ),
            "minimum_complete_sample_size": (
                self.minimum_complete_sample_size
            ),
            "grouping_dimensions": list(
                self.grouping_dimensions
            ),
            "missing_evidence_policy": self.missing_evidence_policy,
            "uncertainty_policy": self.uncertainty_policy,
            "claim_policy": self.claim_policy,
        }

    @classmethod
    def descriptive_v1(
        cls,
        *,
        allowed_methodology_identities: tuple[str, ...],
        minimum_complete_sample_size: int,
        grouping_dimensions: tuple[str, ...] | None = None,
    ) -> "HistoricalOutcomeResearchProtocol":
        """
        Build the Sprint 16 descriptive-only research protocol.

        The minimum sample size is intentionally supplied by the caller rather
        than pretending that one universal threshold is statistically correct.
        """
        return cls(
            protocol_id=cls.DESCRIPTIVE_OUTCOME_RESEARCH,
            version=1,
            allowed_methodology_identities=allowed_methodology_identities,
            eligible_statuses=(
                cls.COMPLETE,
            ),
            minimum_complete_sample_size=minimum_complete_sample_size,
            grouping_dimensions=(
                cls.REQUIRED_GROUPING_DIMENSIONS
                if grouping_dimensions is None
                else grouping_dimensions
            ),
            missing_evidence_policy=cls.KEEP_VISIBLE,
            uncertainty_policy=cls.SAMPLE_STANDARD_ERROR,
            claim_policy=cls.DESCRIPTIVE_ONLY,
        )

"""
Canonical immutable methodology identity contracts for historical outcomes.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.utils.validation import (
    normalize_required_text,
)


def _normalize_positive_version(
    value: object,
    *,
    field_name: str,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value <= 0
    ):
        raise ValueError(
            f"{field_name} must be a positive integer"
        )

    return value


@dataclass(frozen=True, slots=True)
class HistoricalEndpointPolicy:
    """
    Identity of the deterministic endpoint-resolution policy.

    This value object describes methodology only. It does not resolve an
    endpoint, inspect market data, or access a calendar.
    """

    policy_id: str
    version: int

    ELAPSED_DURATION_UTC: ClassVar[str] = "ELAPSED_DURATION_UTC"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_id",
            normalize_required_text(
                self.policy_id,
                field_name="policy_id",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "version",
            _normalize_positive_version(
                self.version,
                field_name="version",
            ),
        )

    @property
    def identity_key(
        self,
    ) -> str:
        return (
            f"{self.policy_id}"
            f"@{self.version}"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "identity_key": self.identity_key,
        }


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceSelectionPolicy:
    """
    Identity of the deterministic historical price-evidence selection policy.

    Selection execution belongs to an evidence adapter/provider, not this
    value object.
    """

    policy_id: str
    version: int
    price_field: str

    EXACT_TIMESTAMP_CLOSE: ClassVar[str] = "EXACT_TIMESTAMP_CLOSE"
    CLOSE: ClassVar[str] = "CLOSE"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_id",
            normalize_required_text(
                self.policy_id,
                field_name="policy_id",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "version",
            _normalize_positive_version(
                self.version,
                field_name="version",
            ),
        )
        object.__setattr__(
            self,
            "price_field",
            normalize_required_text(
                self.price_field,
                field_name="price_field",
                uppercase=True,
            ),
        )

    @property
    def identity_key(
        self,
    ) -> str:
        return (
            f"{self.policy_id}"
            f"@{self.version}"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "price_field": self.price_field,
            "identity_key": self.identity_key,
        }


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeMethodology:
    """
    Versioned identity for one historical outcome observation methodology.

    A methodology names the contracts that determine window interpretation,
    endpoint resolution, and historical price-evidence selection. It does not
    itself perform those operations.
    """

    methodology_id: str
    version: int
    window_kind: str
    endpoint_policy: HistoricalEndpointPolicy
    evidence_selection_policy: HistoricalEvidenceSelectionPolicy

    SPRINT_14_EXACT: ClassVar[str] = "ELAPSED_DAYS_EXACT_CLOSE"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "methodology_id",
            normalize_required_text(
                self.methodology_id,
                field_name="methodology_id",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "version",
            _normalize_positive_version(
                self.version,
                field_name="version",
            ),
        )
        object.__setattr__(
            self,
            "window_kind",
            normalize_required_text(
                self.window_kind,
                field_name="window_kind",
                uppercase=True,
            ),
        )

        if not isinstance(
            self.endpoint_policy,
            HistoricalEndpointPolicy,
        ):
            raise TypeError(
                "endpoint_policy must be a HistoricalEndpointPolicy"
            )

        if not isinstance(
            self.evidence_selection_policy,
            HistoricalEvidenceSelectionPolicy,
        ):
            raise TypeError(
                "evidence_selection_policy must be "
                "a HistoricalEvidenceSelectionPolicy"
            )

    @property
    def identity_key(
        self,
    ) -> str:
        return (
            f"{self.methodology_id}"
            f"@{self.version}"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "methodology_id": self.methodology_id,
            "version": self.version,
            "identity_key": self.identity_key,
            "window_kind": self.window_kind,
            "endpoint_policy": self.endpoint_policy.to_dict(),
            "evidence_selection_policy": (
                self.evidence_selection_policy.to_dict()
            ),
        }

    @classmethod
    def sprint_14_exact_close_v1(
        cls,
    ) -> "HistoricalOutcomeMethodology":
        """
        Name the already-implemented Sprint 14 behavior without changing it.

        Semantics:
        - ELAPSED_DAYS observation window;
        - endpoint = absolute elapsed duration resolved in UTC;
        - exact timestamp match in local candle evidence;
        - candle CLOSE price.
        """
        return cls(
            methodology_id=cls.SPRINT_14_EXACT,
            version=1,
            window_kind="ELAPSED_DAYS",
            endpoint_policy=HistoricalEndpointPolicy(
                policy_id=(
                    HistoricalEndpointPolicy.ELAPSED_DURATION_UTC
                ),
                version=1,
            ),
            evidence_selection_policy=HistoricalEvidenceSelectionPolicy(
                policy_id=(
                    HistoricalEvidenceSelectionPolicy.EXACT_TIMESTAMP_CLOSE
                ),
                version=1,
                price_field=HistoricalEvidenceSelectionPolicy.CLOSE,
            ),
        )

"""
Deterministic historical price-evidence selection policies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalEvidenceSelectionPolicy,
)
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
    HistoricalPricePoint,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalSelectedPriceEvidence:
    """
    Selected historical price point plus explicit selection provenance.
    """

    target_at: datetime
    selection_policy: HistoricalEvidenceSelectionPolicy
    price_point: HistoricalPricePoint

    def __post_init__(self) -> None:
        validate_aware_datetime(
            self.target_at,
            field_name="target_at",
        )

        if not isinstance(
            self.selection_policy,
            HistoricalEvidenceSelectionPolicy,
        ):
            raise TypeError(
                "selection_policy must be a HistoricalEvidenceSelectionPolicy"
            )

        if not isinstance(
            self.price_point,
            HistoricalPricePoint,
        ):
            raise TypeError(
                "price_point must be a HistoricalPricePoint"
            )

        if self.price_point.observed_at != self.target_at:
            raise ValueError(
                "selected price point must exactly match target_at"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "target_at": self.target_at.isoformat(),
            "selection_policy": self.selection_policy.to_dict(),
            "price_point": self.price_point.to_dict(),
        }


class HistoricalPriceEvidenceSelectionService:
    """
    Apply narrow deterministic evidence-selection policies.

    Supported v1 policies remain exact-only:
    - EXACT_TIMESTAMP_CLOSE
    - SESSION_CLOSE_EXACT

    No nearest-date, previous-close, next-close, or current-price fallback exists.
    """

    EXACT_TIMESTAMP_CLOSE: ClassVar[str] = "EXACT_TIMESTAMP_CLOSE"
    SESSION_CLOSE_EXACT: ClassVar[str] = "SESSION_CLOSE_EXACT"

    SUPPORTED_POLICIES: ClassVar[tuple[str, ...]] = (
        EXACT_TIMESTAMP_CLOSE,
        SESSION_CLOSE_EXACT,
    )

    def __init__(
        self,
        provider: HistoricalOutcomePriceEvidenceProvider,
    ) -> None:
        if not isinstance(
            provider,
            HistoricalOutcomePriceEvidenceProvider,
        ):
            raise TypeError(
                "provider must be a HistoricalOutcomePriceEvidenceProvider"
            )

        self.provider = provider

    def select_exact_timestamp(
        self,
        *,
        instrument_key: str,
        resolution: str,
        target_at: datetime,
        policy: HistoricalEvidenceSelectionPolicy,
    ) -> HistoricalSelectedPriceEvidence | None:
        """
        Select only a candle whose timestamp exactly equals target_at.
        """
        self._validate_policy(
            policy,
            expected_policy_id=self.EXACT_TIMESTAMP_CLOSE,
        )
        validate_aware_datetime(
            target_at,
            field_name="target_at",
        )

        point = self.provider.get_exact(
            instrument_key=instrument_key,
            resolution=resolution,
            observed_at=target_at,
        )

        if point is None:
            return None

        return HistoricalSelectedPriceEvidence(
            target_at=point.observed_at,
            selection_policy=policy,
            price_point=point,
        )

    def select_session_close(
        self,
        *,
        instrument_key: str,
        resolution: str,
        session: HistoricalMarketSession,
        policy: HistoricalEvidenceSelectionPolicy,
    ) -> HistoricalSelectedPriceEvidence | None:
        """
        Select only exact evidence at the explicit session close timestamp.
        """
        self._validate_policy(
            policy,
            expected_policy_id=self.SESSION_CLOSE_EXACT,
        )

        if not isinstance(
            session,
            HistoricalMarketSession,
        ):
            raise TypeError(
                "session must be a HistoricalMarketSession"
            )

        point = self.provider.get_exact(
            instrument_key=instrument_key,
            resolution=resolution,
            observed_at=session.closes_at,
        )

        if point is None:
            return None

        return HistoricalSelectedPriceEvidence(
            target_at=point.observed_at,
            selection_policy=policy,
            price_point=point,
        )

    @classmethod
    def exact_timestamp_close_v1(
        cls,
    ) -> HistoricalEvidenceSelectionPolicy:
        return HistoricalEvidenceSelectionPolicy(
            policy_id=cls.EXACT_TIMESTAMP_CLOSE,
            version=1,
            price_field=HistoricalEvidenceSelectionPolicy.CLOSE,
        )

    @classmethod
    def session_close_exact_v1(
        cls,
    ) -> HistoricalEvidenceSelectionPolicy:
        return HistoricalEvidenceSelectionPolicy(
            policy_id=cls.SESSION_CLOSE_EXACT,
            version=1,
            price_field=HistoricalEvidenceSelectionPolicy.CLOSE,
        )

    @classmethod
    def _validate_policy(
        cls,
        policy: HistoricalEvidenceSelectionPolicy,
        *,
        expected_policy_id: str,
    ) -> None:
        if not isinstance(
            policy,
            HistoricalEvidenceSelectionPolicy,
        ):
            raise TypeError(
                "policy must be a HistoricalEvidenceSelectionPolicy"
            )

        normalized_expected = normalize_required_text(
            expected_policy_id,
            field_name="expected_policy_id",
            uppercase=True,
        )

        if policy.policy_id not in cls.SUPPORTED_POLICIES:
            raise ValueError(
                "unsupported evidence-selection policy: "
                f"{policy.policy_id}"
            )

        if policy.policy_id != normalized_expected:
            raise ValueError(
                "evidence-selection policy does not match requested selector"
            )

        if policy.price_field != HistoricalEvidenceSelectionPolicy.CLOSE:
            raise ValueError(
                "only CLOSE price field is supported"
            )

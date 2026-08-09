"""
Methodology-aware historical price-evidence contracts and adapter service.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
    HistoricalSelectedPriceEvidence,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalMarketSession,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalMethodologyAwarePriceEvidence:
    """
    Historical price evidence with explicit methodology and selection identity.
    """

    methodology: HistoricalOutcomeMethodology
    intended_endpoint_at: datetime
    selected_evidence: HistoricalSelectedPriceEvidence
    session: HistoricalMarketSession | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.methodology,
            HistoricalOutcomeMethodology,
        ):
            raise TypeError(
                "methodology must be a HistoricalOutcomeMethodology"
            )

        validate_aware_datetime(
            self.intended_endpoint_at,
            field_name="intended_endpoint_at",
        )

        if not isinstance(
            self.selected_evidence,
            HistoricalSelectedPriceEvidence,
        ):
            raise TypeError(
                "selected_evidence must be a HistoricalSelectedPriceEvidence"
            )

        if (
            self.selected_evidence.selection_policy
            != self.methodology.evidence_selection_policy
        ):
            raise ValueError(
                "selected evidence policy must match methodology"
            )

        if (
            self.selected_evidence.target_at
            != self.intended_endpoint_at
        ):
            raise ValueError(
                "selected evidence target must match intended endpoint"
            )

        if self.session is not None:
            if not isinstance(
                self.session,
                HistoricalMarketSession,
            ):
                raise TypeError(
                    "session must be a HistoricalMarketSession or None"
                )

            if self.session.closes_at != self.intended_endpoint_at:
                raise ValueError(
                    "session close must match intended endpoint"
                )

    @property
    def observed_at(
        self,
    ) -> datetime:
        return self.selected_evidence.price_point.observed_at

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "methodology": self.methodology.to_dict(),
            "intended_endpoint_at": self.intended_endpoint_at.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "session": (
                None
                if self.session is None
                else self.session.to_dict()
            ),
            "selected_evidence": self.selected_evidence.to_dict(),
        }


class HistoricalMethodologyAwarePriceEvidenceService:
    """
    Build methodology-aware price evidence through explicit selection policies.
    """

    def __init__(
        self,
        selection_service: HistoricalPriceEvidenceSelectionService,
    ) -> None:
        if not isinstance(
            selection_service,
            HistoricalPriceEvidenceSelectionService,
        ):
            raise TypeError(
                "selection_service must be a "
                "HistoricalPriceEvidenceSelectionService"
            )

        self.selection_service = selection_service

    def select_for_exact_timestamp(
        self,
        *,
        methodology: HistoricalOutcomeMethodology,
        instrument_key: str,
        resolution: str,
        target_at: datetime,
    ) -> HistoricalMethodologyAwarePriceEvidence | None:
        self._validate_methodology(
            methodology
        )
        validate_aware_datetime(
            target_at,
            field_name="target_at",
        )

        selected = self.selection_service.select_exact_timestamp(
            instrument_key=instrument_key,
            resolution=resolution,
            target_at=target_at,
            policy=methodology.evidence_selection_policy,
        )

        if selected is None:
            return None

        return HistoricalMethodologyAwarePriceEvidence(
            methodology=methodology,
            intended_endpoint_at=target_at,
            selected_evidence=selected,
            session=None,
        )

    def select_for_session_close(
        self,
        *,
        methodology: HistoricalOutcomeMethodology,
        instrument_key: str,
        resolution: str,
        session: HistoricalMarketSession,
    ) -> HistoricalMethodologyAwarePriceEvidence | None:
        self._validate_methodology(
            methodology
        )

        if not isinstance(
            session,
            HistoricalMarketSession,
        ):
            raise TypeError(
                "session must be a HistoricalMarketSession"
            )

        selected = self.selection_service.select_session_close(
            instrument_key=instrument_key,
            resolution=resolution,
            session=session,
            policy=methodology.evidence_selection_policy,
        )

        if selected is None:
            return None

        return HistoricalMethodologyAwarePriceEvidence(
            methodology=methodology,
            intended_endpoint_at=session.closes_at,
            selected_evidence=selected,
            session=session,
        )

    @staticmethod
    def _validate_methodology(
        methodology: HistoricalOutcomeMethodology,
    ) -> None:
        if not isinstance(
            methodology,
            HistoricalOutcomeMethodology,
        ):
            raise TypeError(
                "methodology must be a HistoricalOutcomeMethodology"
            )

"""
Methodology-aware historical outcome observation orchestration.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
    HistoricalSelectedPriceEvidence,
)
from investment_terminal.history.historical_methodology_aware_price_evidence import (
    HistoricalMethodologyAwarePriceEvidence,
    HistoricalMethodologyAwarePriceEvidenceService,
)
from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
)
from investment_terminal.history.historical_trading_session_window import (
    HistoricalTradingSessionWindowPolicy,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalMethodologyAwareObservationResult:
    """Observation, calculation, and explicit methodology/evidence provenance."""

    methodology: HistoricalOutcomeMethodology
    observation: HistoricalRecommendationObservation
    outcome: HistoricalRecommendationOutcome | None
    origin_selected_evidence: HistoricalSelectedPriceEvidence | None
    endpoint_methodology_evidence: HistoricalMethodologyAwarePriceEvidence | None

    def __post_init__(self) -> None:
        if not isinstance(self.methodology, HistoricalOutcomeMethodology):
            raise TypeError(
                "methodology must be a HistoricalOutcomeMethodology"
            )
        if not isinstance(self.observation, HistoricalRecommendationObservation):
            raise TypeError(
                "observation must be a HistoricalRecommendationObservation"
            )
        if (
            self.outcome is not None
            and self.observation.status
            != HistoricalRecommendationObservation.COMPLETE
        ):
            raise ValueError(
                "outcome is only valid for COMPLETE observations"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "methodology": self.methodology.to_dict(),
            "observation": self.observation.to_dict(),
            "outcome": (
                None
                if self.outcome is None
                else self.outcome.to_dict()
            ),
            "origin_selected_evidence": (
                None
                if self.origin_selected_evidence is None
                else self.origin_selected_evidence.to_dict()
            ),
            "endpoint_methodology_evidence": (
                None
                if self.endpoint_methodology_evidence is None
                else self.endpoint_methodology_evidence.to_dict()
            ),
        }


class HistoricalMethodologyAwareObservationService:
    """
    Observe one recommendation through an explicit outcome methodology.

    Origin evidence is always exact at the historical recommendation timestamp.
    Endpoint resolution/selection follows the supplied methodology.
    """

    RAW_PRICE_WARNING = (
        "Raw close-price movement only; not portfolio performance "
        "and not evidence of causality"
    )

    def __init__(
        self,
        *,
        elapsed_window_policy: HistoricalObservationWindowPolicy,
        trading_session_window_policy: HistoricalTradingSessionWindowPolicy,
        selection_service: HistoricalPriceEvidenceSelectionService,
        methodology_evidence_service: HistoricalMethodologyAwarePriceEvidenceService,
        calculator: HistoricalRecommendationOutcomeCalculator,
    ) -> None:
        self.elapsed_window_policy = elapsed_window_policy
        self.trading_session_window_policy = trading_session_window_policy
        self.selection_service = selection_service
        self.methodology_evidence_service = methodology_evidence_service
        self.calculator = calculator

    def observe(
        self,
        *,
        state: HistoricalRecommendationState,
        window: HistoricalObservationWindow,
        methodology: HistoricalOutcomeMethodology,
        as_of: datetime,
        resolution: str,
    ) -> HistoricalMethodologyAwareObservationResult:
        if not isinstance(state, HistoricalRecommendationState):
            raise TypeError(
                "state must be a HistoricalRecommendationState"
            )
        if not isinstance(window, HistoricalObservationWindow):
            raise TypeError(
                "window must be a HistoricalObservationWindow"
            )
        if not isinstance(methodology, HistoricalOutcomeMethodology):
            raise TypeError(
                "methodology must be a HistoricalOutcomeMethodology"
            )
        validate_aware_datetime(as_of, field_name="as_of")
        normalized_resolution = normalize_required_text(
            resolution,
            field_name="resolution",
            uppercase=True,
        )

        if methodology.window_kind != window.kind:
            raise ValueError(
                "methodology window_kind must match observation window kind"
            )

        if not state.present or state.symbol is None:
            return self._result_without_outcome(
                state=state,
                window=window,
                methodology=methodology,
                status=HistoricalRecommendationObservation.UNAVAILABLE,
                evidence=None,
                origin_selected=None,
                endpoint_methodology_evidence=None,
                warning=(
                    "Recommendation is absent or has no symbol at the "
                    "observation origin snapshot"
                ),
            )

        origin_selected = self.selection_service.select_exact_timestamp(
            instrument_key=state.symbol,
            resolution=normalized_resolution,
            target_at=state.generated_at,
            policy=self.selection_service.exact_timestamp_close_v1(),
        )

        endpoint_at: datetime
        endpoint_methodology_evidence: HistoricalMethodologyAwarePriceEvidence | None

        if window.kind == "ELAPSED_DAYS":
            resolved = self.elapsed_window_policy.resolve(
                origin_at=state.generated_at,
                window=window,
                as_of=as_of,
            )
            endpoint_at = resolved.endpoint_at

            if not resolved.is_mature:
                evidence = self._evidence(
                    state=state,
                    endpoint_at=endpoint_at,
                    origin_selected=origin_selected,
                    endpoint_selected=None,
                )
                return self._result_without_outcome(
                    state=state,
                    window=window,
                    methodology=methodology,
                    status=HistoricalRecommendationObservation.NOT_MATURE,
                    evidence=evidence,
                    origin_selected=origin_selected,
                    endpoint_methodology_evidence=None,
                    warning="Observation window has not matured",
                )

            endpoint_methodology_evidence = (
                self.methodology_evidence_service.select_for_exact_timestamp(
                    methodology=methodology,
                    instrument_key=state.symbol,
                    resolution=normalized_resolution,
                    target_at=endpoint_at,
                )
            )

        elif window.kind == "TRADING_SESSIONS":
            resolved = self.trading_session_window_policy.resolve(
                origin_at=state.generated_at,
                window=window,
                as_of=as_of,
            )
            endpoint_at = resolved.endpoint_at

            if not resolved.is_mature:
                evidence = self._evidence(
                    state=state,
                    endpoint_at=endpoint_at,
                    origin_selected=origin_selected,
                    endpoint_selected=None,
                )
                return self._result_without_outcome(
                    state=state,
                    window=window,
                    methodology=methodology,
                    status=HistoricalRecommendationObservation.NOT_MATURE,
                    evidence=evidence,
                    origin_selected=origin_selected,
                    endpoint_methodology_evidence=None,
                    warning="Observation window has not matured",
                )

            endpoint_methodology_evidence = (
                self.methodology_evidence_service.select_for_session_close(
                    methodology=methodology,
                    instrument_key=state.symbol,
                    resolution=normalized_resolution,
                    session=resolved.endpoint_session,
                )
            )
        else:
            raise ValueError(
                f"unsupported methodology window kind: {window.kind}"
            )

        endpoint_selected = (
            None
            if endpoint_methodology_evidence is None
            else endpoint_methodology_evidence.selected_evidence
        )
        evidence = self._evidence(
            state=state,
            endpoint_at=endpoint_at,
            origin_selected=origin_selected,
            endpoint_selected=endpoint_selected,
        )

        if origin_selected is None and endpoint_selected is None:
            status = HistoricalRecommendationObservation.UNAVAILABLE
            warning = "Exact origin and endpoint price evidence are unavailable"
        elif origin_selected is None or endpoint_selected is None:
            status = HistoricalRecommendationObservation.PARTIAL
            warning = "Exact origin or endpoint price evidence is unavailable"
        elif (
            origin_selected.price_point.currency
            != endpoint_selected.price_point.currency
        ):
            status = HistoricalRecommendationObservation.PARTIAL
            warning = (
                "Origin and endpoint currencies differ; FX-adjusted "
                "outcome calculation is not supported"
            )
        else:
            observation = self._observation(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.COMPLETE,
                evidence=evidence,
                warnings=(self.RAW_PRICE_WARNING,),
            )
            outcome = self.calculator.calculate(
                evidence=evidence,
                origin_currency=origin_selected.price_point.currency,
                endpoint_currency=endpoint_selected.price_point.currency,
            )
            return HistoricalMethodologyAwareObservationResult(
                methodology=methodology,
                observation=observation,
                outcome=outcome,
                origin_selected_evidence=origin_selected,
                endpoint_methodology_evidence=endpoint_methodology_evidence,
            )

        return self._result_without_outcome(
            state=state,
            window=window,
            methodology=methodology,
            status=status,
            evidence=evidence,
            origin_selected=origin_selected,
            endpoint_methodology_evidence=endpoint_methodology_evidence,
            warning=warning,
        )

    @staticmethod
    def _evidence(
        *,
        state: HistoricalRecommendationState,
        endpoint_at: datetime,
        origin_selected: HistoricalSelectedPriceEvidence | None,
        endpoint_selected: HistoricalSelectedPriceEvidence | None,
    ) -> HistoricalOutcomeEvidence:
        origin_point = (
            None if origin_selected is None else origin_selected.price_point
        )
        endpoint_point = (
            None if endpoint_selected is None else endpoint_selected.price_point
        )

        return HistoricalOutcomeEvidence(
            instrument_key=state.symbol or state.recommendation_key,
            origin_at=state.generated_at,
            endpoint_at=endpoint_at,
            origin_price=None if origin_point is None else origin_point.price,
            endpoint_price=None if endpoint_point is None else endpoint_point.price,
            origin_source=None if origin_point is None else origin_point.source,
            endpoint_source=None if endpoint_point is None else endpoint_point.source,
            origin_currency=None if origin_point is None else origin_point.currency,
            endpoint_currency=None if endpoint_point is None else endpoint_point.currency,
            origin_resolution=None if origin_point is None else origin_point.resolution,
            endpoint_resolution=None if endpoint_point is None else endpoint_point.resolution,
        )

    @classmethod
    def _result_without_outcome(
        cls,
        *,
        state: HistoricalRecommendationState,
        window: HistoricalObservationWindow,
        methodology: HistoricalOutcomeMethodology,
        status: str,
        evidence: HistoricalOutcomeEvidence | None,
        origin_selected: HistoricalSelectedPriceEvidence | None,
        endpoint_methodology_evidence: HistoricalMethodologyAwarePriceEvidence | None,
        warning: str,
    ) -> HistoricalMethodologyAwareObservationResult:
        return HistoricalMethodologyAwareObservationResult(
            methodology=methodology,
            observation=cls._observation(
                state=state,
                window=window,
                status=status,
                evidence=evidence,
                warnings=(warning,),
            ),
            outcome=None,
            origin_selected_evidence=origin_selected,
            endpoint_methodology_evidence=endpoint_methodology_evidence,
        )

    @staticmethod
    def _observation(
        *,
        state: HistoricalRecommendationState,
        window: HistoricalObservationWindow,
        status: str,
        evidence: HistoricalOutcomeEvidence | None,
        warnings: tuple[str, ...],
    ) -> HistoricalRecommendationObservation:
        return HistoricalRecommendationObservation(
            origin_snapshot_id=state.snapshot_id,
            recommendation_key=state.recommendation_key,
            symbol=state.symbol,
            action=state.action,
            origin_at=state.generated_at,
            window=window,
            status=status,
            evidence=evidence,
            warnings=warnings,
        )

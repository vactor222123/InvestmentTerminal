"""
Application service for one historical recommendation outcome observation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcome,
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
    HistoricalOutcomeEvidence,
    HistoricalRecommendationObservation,
)
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
    HistoricalPricePoint,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeObservationResult:
    """Observation envelope plus optional calculated raw price movement."""

    observation: HistoricalRecommendationObservation
    outcome: HistoricalRecommendationOutcome | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.observation,
            HistoricalRecommendationObservation,
        ):
            raise TypeError(
                "observation must be a HistoricalRecommendationObservation"
            )

        if (
            self.outcome is not None
            and not isinstance(
                self.outcome,
                HistoricalRecommendationOutcome,
            )
        ):
            raise TypeError(
                "outcome must be a HistoricalRecommendationOutcome or None"
            )

        if (
            self.outcome is not None
            and self.observation.status
            != HistoricalRecommendationObservation.COMPLETE
        ):
            raise ValueError(
                "outcome is only valid for COMPLETE observations"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "observation": self.observation.to_dict(),
            "outcome": (
                None
                if self.outcome is None
                else self.outcome.to_dict()
            ),
        }


class HistoricalOutcomeObservationService:
    """
    Orchestrate one recommendation observation from explicit local evidence.

    No SQL, archive mutation, network access, current-price fallback, or
    nearest-date substitution is performed here.
    """

    RAW_PRICE_WARNING = (
        "Raw close-price movement only; not portfolio performance "
        "and not evidence of causality"
    )

    def __init__(
        self,
        *,
        window_policy: HistoricalObservationWindowPolicy,
        price_provider: HistoricalOutcomePriceEvidenceProvider,
        calculator: HistoricalRecommendationOutcomeCalculator,
    ) -> None:
        if not isinstance(
            window_policy,
            HistoricalObservationWindowPolicy,
        ):
            raise TypeError(
                "window_policy must be a HistoricalObservationWindowPolicy"
            )
        if not isinstance(
            price_provider,
            HistoricalOutcomePriceEvidenceProvider,
        ):
            raise TypeError(
                "price_provider must be a HistoricalOutcomePriceEvidenceProvider"
            )
        if not isinstance(
            calculator,
            HistoricalRecommendationOutcomeCalculator,
        ):
            raise TypeError(
                "calculator must be a HistoricalRecommendationOutcomeCalculator"
            )

        self.window_policy = window_policy
        self.price_provider = price_provider
        self.calculator = calculator

    def observe(
        self,
        *,
        state: HistoricalRecommendationState,
        window: HistoricalObservationWindow,
        as_of: datetime,
        resolution: str,
    ) -> HistoricalOutcomeObservationResult:
        if not isinstance(
            state,
            HistoricalRecommendationState,
        ):
            raise TypeError(
                "state must be a HistoricalRecommendationState"
            )
        if not isinstance(
            window,
            HistoricalObservationWindow,
        ):
            raise TypeError(
                "window must be a HistoricalObservationWindow"
            )

        validate_aware_datetime(
            as_of,
            field_name="as_of",
        )
        normalized_resolution = normalize_required_text(
            resolution,
            field_name="resolution",
            uppercase=True,
        )

        if not state.present:
            return self._without_outcome(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.UNAVAILABLE,
                evidence=None,
                warnings=(
                    "Recommendation is absent at the observation origin snapshot",
                ),
            )

        if state.symbol is None:
            return self._without_outcome(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.UNAVAILABLE,
                evidence=None,
                warnings=(
                    "Recommendation has no symbol for price-evidence lookup",
                ),
            )

        resolved = self.window_policy.resolve(
            origin_at=state.generated_at,
            window=window,
            as_of=as_of,
        )

        origin = self.price_provider.get_exact(
            instrument_key=state.symbol,
            resolution=normalized_resolution,
            observed_at=resolved.origin_at,
        )

        if not resolved.is_mature:
            evidence = self._evidence(
                instrument_key=state.symbol,
                origin_at=resolved.origin_at,
                endpoint_at=resolved.endpoint_at,
                origin=origin,
                endpoint=None,
            )
            return self._without_outcome(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.NOT_MATURE,
                evidence=evidence,
                warnings=(
                    "Observation window has not matured",
                ),
            )

        endpoint = self.price_provider.get_exact(
            instrument_key=state.symbol,
            resolution=normalized_resolution,
            observed_at=resolved.endpoint_at,
        )

        evidence = self._evidence(
            instrument_key=state.symbol,
            origin_at=resolved.origin_at,
            endpoint_at=resolved.endpoint_at,
            origin=origin,
            endpoint=endpoint,
        )

        if origin is None and endpoint is None:
            return self._without_outcome(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.UNAVAILABLE,
                evidence=evidence,
                warnings=(
                    "Exact origin and endpoint price evidence are unavailable",
                ),
            )

        if origin is None or endpoint is None:
            missing = (
                "origin"
                if origin is None
                else "endpoint"
            )
            return self._without_outcome(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.PARTIAL,
                evidence=evidence,
                warnings=(
                    f"Exact {missing} price evidence is unavailable",
                ),
            )

        if origin.currency != endpoint.currency:
            return self._without_outcome(
                state=state,
                window=window,
                status=HistoricalRecommendationObservation.PARTIAL,
                evidence=evidence,
                warnings=(
                    "Origin and endpoint currencies differ; FX-adjusted "
                    "outcome calculation is not supported",
                ),
            )

        observation = self._observation(
            state=state,
            window=window,
            status=HistoricalRecommendationObservation.COMPLETE,
            evidence=evidence,
            warnings=(
                self.RAW_PRICE_WARNING,
            ),
        )
        outcome = self.calculator.calculate(
            evidence=evidence,
            origin_currency=origin.currency,
            endpoint_currency=endpoint.currency,
        )

        return HistoricalOutcomeObservationResult(
            observation=observation,
            outcome=outcome,
        )

    @staticmethod
    def _evidence(
        *,
        instrument_key: str,
        origin_at: datetime,
        endpoint_at: datetime,
        origin: HistoricalPricePoint | None,
        endpoint: HistoricalPricePoint | None,
    ) -> HistoricalOutcomeEvidence:
        return HistoricalOutcomeEvidence(
            instrument_key=instrument_key,
            origin_at=origin_at,
            endpoint_at=endpoint_at,
            origin_price=(
                None
                if origin is None
                else origin.price
            ),
            endpoint_price=(
                None
                if endpoint is None
                else endpoint.price
            ),
            origin_source=(
                None
                if origin is None
                else origin.source
            ),
            endpoint_source=(
                None
                if endpoint is None
                else endpoint.source
            ),
            origin_currency=(
                None
                if origin is None
                else origin.currency
            ),
            endpoint_currency=(
                None
                if endpoint is None
                else endpoint.currency
            ),
            origin_resolution=(
                None
                if origin is None
                else origin.resolution
            ),
            endpoint_resolution=(
                None
                if endpoint is None
                else endpoint.resolution
            ),
        )

    @classmethod
    def _without_outcome(
        cls,
        *,
        state: HistoricalRecommendationState,
        window: HistoricalObservationWindow,
        status: str,
        evidence: HistoricalOutcomeEvidence | None,
        warnings: tuple[str, ...],
    ) -> HistoricalOutcomeObservationResult:
        return HistoricalOutcomeObservationResult(
            observation=cls._observation(
                state=state,
                window=window,
                status=status,
                evidence=evidence,
                warnings=warnings,
            ),
            outcome=None,
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

"""
Protocol-aware orchestration for historical outcome research.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_cohort import (
    HistoricalOutcomeCohortKey,
    HistoricalOutcomeCohortService,
)
from investment_terminal.history.historical_outcome_descriptive_summary import (
    HistoricalOutcomeDescriptiveSummary,
    HistoricalOutcomeDescriptiveSummaryService,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
)
from investment_terminal.history.historical_outcome_research_claim_boundary import (
    HistoricalOutcomeResearchClaimAssessment,
    HistoricalOutcomeResearchClaimBoundaryService,
)
from investment_terminal.history.historical_outcome_research_coverage import (
    HistoricalOutcomeResearchCoverage,
    HistoricalOutcomeResearchCoverageService,
)
from investment_terminal.history.historical_outcome_research_eligibility import (
    HistoricalOutcomeEligibilityService,
)
from investment_terminal.history.historical_outcome_research_population import (
    HistoricalOutcomeResearchPopulationMetadata,
    HistoricalOutcomeResearchPopulationMetadataService,
)
from investment_terminal.history.historical_outcome_research_population_frame import (
    HistoricalOutcomeResearchPopulationFrame,
    HistoricalOutcomeResearchPopulationFrameService,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_sample_sufficiency import (
    HistoricalOutcomeSampleAssessment,
    HistoricalOutcomeSampleSufficiencyService,
)
from investment_terminal.history.historical_outcome_uncertainty import (
    HistoricalOutcomeUncertaintyService,
    HistoricalOutcomeUncertaintySummary,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchCohortResult:
    """One complete protocol-aware research result for an exact cohort."""

    protocol_identity: str
    population_frame: HistoricalOutcomeResearchPopulationFrame
    population: HistoricalOutcomeResearchPopulationMetadata
    cohort: HistoricalOutcomeCohortKey
    coverage: HistoricalOutcomeResearchCoverage
    sample_assessment: HistoricalOutcomeSampleAssessment
    descriptive_summary: HistoricalOutcomeDescriptiveSummary | None
    uncertainty: HistoricalOutcomeUncertaintySummary | None
    claim_assessment: HistoricalOutcomeResearchClaimAssessment

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_identity": self.protocol_identity,
            "population_frame": self.population_frame.to_dict(),
            "population": self.population.to_dict(),
            "cohort": self.cohort.to_dict(),
            "coverage": self.coverage.to_dict(),
            "sample_assessment": self.sample_assessment.to_dict(),
            "descriptive_summary": (
                None
                if self.descriptive_summary is None
                else self.descriptive_summary.to_dict()
            ),
            "uncertainty": (
                None
                if self.uncertainty is None
                else self.uncertainty.to_dict()
            ),
            "claim_assessment": self.claim_assessment.to_dict(),
        }


class HistoricalOutcomeResearchService:
    """
    Compose research policies without duplicating their logic.

    The service groups exact cohorts, preserves coverage for all selected
    candidates, records pre-selection population provenance, assesses
    sufficiency, summarizes eligible COMPLETE outcomes descriptively, reports
    uncertainty, carries population-selection metadata, and applies the explicit
    claim boundary.
    """

    def __init__(
        self,
        *,
        cohort_service: HistoricalOutcomeCohortService | None = None,
        eligibility_service: HistoricalOutcomeEligibilityService | None = None,
        coverage_service: HistoricalOutcomeResearchCoverageService | None = None,
        sample_service: HistoricalOutcomeSampleSufficiencyService | None = None,
        descriptive_service: HistoricalOutcomeDescriptiveSummaryService | None = None,
        uncertainty_service: HistoricalOutcomeUncertaintyService | None = None,
        claim_service: HistoricalOutcomeResearchClaimBoundaryService | None = None,
        population_service: (
            HistoricalOutcomeResearchPopulationMetadataService | None
        ) = None,
        population_frame_service: (
            HistoricalOutcomeResearchPopulationFrameService | None
        ) = None,
    ) -> None:
        self._cohort_service = (
            cohort_service
            if cohort_service is not None
            else HistoricalOutcomeCohortService()
        )
        self._eligibility_service = (
            eligibility_service
            if eligibility_service is not None
            else HistoricalOutcomeEligibilityService()
        )
        self._coverage_service = (
            coverage_service
            if coverage_service is not None
            else HistoricalOutcomeResearchCoverageService(
                eligibility_service=self._eligibility_service,
            )
        )
        self._sample_service = (
            sample_service
            if sample_service is not None
            else HistoricalOutcomeSampleSufficiencyService()
        )
        self._descriptive_service = (
            descriptive_service
            if descriptive_service is not None
            else HistoricalOutcomeDescriptiveSummaryService()
        )
        self._uncertainty_service = (
            uncertainty_service
            if uncertainty_service is not None
            else HistoricalOutcomeUncertaintyService()
        )
        self._claim_service = (
            claim_service
            if claim_service is not None
            else HistoricalOutcomeResearchClaimBoundaryService()
        )
        self._population_service = (
            population_service
            if population_service is not None
            else HistoricalOutcomeResearchPopulationMetadataService()
        )
        self._population_frame_service = (
            population_frame_service
            if population_frame_service is not None
            else HistoricalOutcomeResearchPopulationFrameService()
        )

    def analyze(
        self,
        *,
        results: tuple[
            HistoricalMethodologyAwareObservationResult,
            ...,
        ],
        protocol: HistoricalOutcomeResearchProtocol,
        population_query: HistoricalOutcomeQuery | None = None,
        source_observation_count: int | None = None,
    ) -> tuple[HistoricalOutcomeResearchCohortResult, ...]:
        if not isinstance(results, tuple):
            raise TypeError(
                "results must be a tuple"
            )
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )
        if (
            population_query is not None
            and not isinstance(
                population_query,
                HistoricalOutcomeQuery,
            )
        ):
            raise TypeError(
                "population_query must be a HistoricalOutcomeQuery or None"
            )

        selected_candidate_count = len(results)
        effective_source_count = (
            selected_candidate_count
            if source_observation_count is None
            else source_observation_count
        )
        population_frame = self._population_frame_service.build(
            source_observation_count=effective_source_count,
            selected_candidate_count=selected_candidate_count,
        )

        effective_query = (
            HistoricalOutcomeQuery()
            if population_query is None
            else population_query
        )
        population = self._population_service.build(
            query=effective_query,
            candidate_count=selected_candidate_count,
        )

        grouped = self._cohort_service.group(
            results=results,
            protocol=protocol,
        )

        return tuple(
            self._analyze_cohort(
                cohort=cohort,
                results=cohort_results,
                protocol=protocol,
                population=population,
                population_frame=population_frame,
            )
            for cohort, cohort_results in grouped
        )

    def _analyze_cohort(
        self,
        *,
        cohort: HistoricalOutcomeCohortKey,
        results: tuple[
            HistoricalMethodologyAwareObservationResult,
            ...,
        ],
        protocol: HistoricalOutcomeResearchProtocol,
        population: HistoricalOutcomeResearchPopulationMetadata,
        population_frame: HistoricalOutcomeResearchPopulationFrame,
    ) -> HistoricalOutcomeResearchCohortResult:
        coverage = self._coverage_service.summarize(
            results=results,
            protocol=protocol,
        )
        sample_assessment = self._sample_service.assess(
            coverage=coverage,
            protocol=protocol,
        )

        assessments = self._eligibility_service.assess_many(
            results=results,
            protocol=protocol,
        )

        eligible_outcomes = []
        for result, assessment in zip(
            results,
            assessments,
            strict=True,
        ):
            if not assessment.eligible:
                continue
            if result.outcome is None:
                raise ValueError(
                    "eligible observation must contain a calculated outcome"
                )
            eligible_outcomes.append(
                result.outcome
            )

        descriptive_summary = self._descriptive_service.summarize(
            outcomes=tuple(
                eligible_outcomes
            ),
        )
        uncertainty = (
            None
            if descriptive_summary is None
            else self._uncertainty_service.summarize(
                descriptive_summary=descriptive_summary,
                protocol=protocol,
            )
        )
        claim_assessment = self._claim_service.assess(
            protocol=protocol,
            sample_assessment=sample_assessment,
        )

        return HistoricalOutcomeResearchCohortResult(
            protocol_identity=protocol.identity_key,
            population_frame=population_frame,
            population=population,
            cohort=cohort,
            coverage=coverage,
            sample_assessment=sample_assessment,
            descriptive_summary=descriptive_summary,
            uncertainty=uncertainty,
            claim_assessment=claim_assessment,
        )

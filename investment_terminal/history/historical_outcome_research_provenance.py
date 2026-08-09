"""
Immutable summary contract for historical outcome research provenance.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from investment_terminal.history.historical_outcome_population_completeness import (
    HistoricalOutcomePopulationCompletenessAssessment,
)
from investment_terminal.history.historical_outcome_research_population_frame import (
    HistoricalOutcomeResearchPopulationFrame,
)
from investment_terminal.history.historical_outcome_selection_accounting import (
    HistoricalOutcomeSelectionAccounting,
)
from investment_terminal.history.historical_outcome_source_import_quality import (
    HistoricalOutcomeSourceImportQualityAssessment,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeResearchProvenanceSummary:
    """
    Stable envelope over independent research-provenance assessments.

    This model deliberately does not collapse provenance into one score or
    pass/fail label. Each component keeps its own semantics.
    """

    population_frame: HistoricalOutcomeResearchPopulationFrame
    selection_accounting: HistoricalOutcomeSelectionAccounting | None
    population_completeness: HistoricalOutcomePopulationCompletenessAssessment | None
    source_import_quality: HistoricalOutcomeSourceImportQualityAssessment | None

    POPULATION_FRAME: ClassVar[str] = "POPULATION_FRAME"
    SELECTION_ACCOUNTING: ClassVar[str] = "SELECTION_ACCOUNTING"
    POPULATION_COMPLETENESS: ClassVar[str] = "POPULATION_COMPLETENESS"
    SOURCE_IMPORT_QUALITY: ClassVar[str] = "SOURCE_IMPORT_QUALITY"

    COMPONENT_ORDER: ClassVar[tuple[str, ...]] = (
        SOURCE_IMPORT_QUALITY,
        POPULATION_COMPLETENESS,
        POPULATION_FRAME,
        SELECTION_ACCOUNTING,
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.population_frame,
            HistoricalOutcomeResearchPopulationFrame,
        ):
            raise TypeError(
                "population_frame must be a "
                "HistoricalOutcomeResearchPopulationFrame"
            )
        if (
            self.selection_accounting is not None
            and not isinstance(
                self.selection_accounting,
                HistoricalOutcomeSelectionAccounting,
            )
        ):
            raise TypeError(
                "selection_accounting must be a "
                "HistoricalOutcomeSelectionAccounting or None"
            )
        if (
            self.population_completeness is not None
            and not isinstance(
                self.population_completeness,
                HistoricalOutcomePopulationCompletenessAssessment,
            )
        ):
            raise TypeError(
                "population_completeness must be a "
                "HistoricalOutcomePopulationCompletenessAssessment or None"
            )
        if (
            self.source_import_quality is not None
            and not isinstance(
                self.source_import_quality,
                HistoricalOutcomeSourceImportQualityAssessment,
            )
        ):
            raise TypeError(
                "source_import_quality must be a "
                "HistoricalOutcomeSourceImportQualityAssessment or None"
            )

        source_count = self.population_frame.source_observation_count

        if (
            self.selection_accounting is not None
            and self.selection_accounting.source_observation_count
            != source_count
        ):
            raise ValueError(
                "selection_accounting source_observation_count must match "
                "population_frame source_observation_count"
            )
        if (
            self.population_completeness is not None
            and self.population_completeness.source_observation_count
            != source_count
        ):
            raise ValueError(
                "population_completeness source_observation_count must match "
                "population_frame source_observation_count"
            )
        if (
            self.source_import_quality is not None
            and self.source_import_quality.source_observation_count
            != source_count
        ):
            raise ValueError(
                "source_import_quality source_observation_count must match "
                "population_frame source_observation_count"
            )

        if (
            self.selection_accounting is not None
            and self.selection_accounting.selected_candidate_count
            != self.population_frame.selected_candidate_count
        ):
            raise ValueError(
                "selection_accounting selected_candidate_count must match "
                "population_frame selected_candidate_count"
            )

    @property
    def available_components(self) -> tuple[str, ...]:
        available = {
            self.POPULATION_FRAME,
        }
        if self.selection_accounting is not None:
            available.add(
                self.SELECTION_ACCOUNTING
            )
        if self.population_completeness is not None:
            available.add(
                self.POPULATION_COMPLETENESS
            )
        if self.source_import_quality is not None:
            available.add(
                self.SOURCE_IMPORT_QUALITY
            )

        return tuple(
            component
            for component in self.COMPONENT_ORDER
            if component in available
        )

    @property
    def missing_components(self) -> tuple[str, ...]:
        available = set(
            self.available_components
        )
        return tuple(
            component
            for component in self.COMPONENT_ORDER
            if component not in available
        )

    @property
    def complete_component_set(self) -> bool:
        return not self.missing_components

    def to_dict(self) -> dict[str, Any]:
        return {
            "population_frame": self.population_frame.to_dict(),
            "selection_accounting": (
                None
                if self.selection_accounting is None
                else self.selection_accounting.to_dict()
            ),
            "population_completeness": (
                None
                if self.population_completeness is None
                else self.population_completeness.to_dict()
            ),
            "source_import_quality": (
                None
                if self.source_import_quality is None
                else self.source_import_quality.to_dict()
            ),
            "available_components": list(
                self.available_components
            ),
            "missing_components": list(
                self.missing_components
            ),
            "complete_component_set": self.complete_component_set,
        }


class HistoricalOutcomeResearchProvenanceSummaryService:
    """Compose validated provenance components without inventing heuristics."""

    def build(
        self,
        *,
        population_frame: HistoricalOutcomeResearchPopulationFrame,
        selection_accounting: HistoricalOutcomeSelectionAccounting | None = None,
        population_completeness: (
            HistoricalOutcomePopulationCompletenessAssessment | None
        ) = None,
        source_import_quality: (
            HistoricalOutcomeSourceImportQualityAssessment | None
        ) = None,
    ) -> HistoricalOutcomeResearchProvenanceSummary:
        return HistoricalOutcomeResearchProvenanceSummary(
            population_frame=population_frame,
            selection_accounting=selection_accounting,
            population_completeness=population_completeness,
            source_import_quality=source_import_quality,
        )

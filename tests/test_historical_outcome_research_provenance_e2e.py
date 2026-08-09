"""
Production-style end-to-end fixture for Sprint 17 research provenance.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
)
from investment_terminal.history.historical_local_session_calendar import (
    HistoricalLocalSessionCalendar,
)
from investment_terminal.history.historical_market_session_models import (
    HistoricalSessionCalendarIdentity,
)
from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationService,
)
from investment_terminal.history.historical_methodology_aware_price_evidence import (
    HistoricalMethodologyAwarePriceEvidenceService,
)
from investment_terminal.history.historical_observation_window import (
    HistoricalObservationWindowPolicy,
)
from investment_terminal.history.historical_outcome_calculator import (
    HistoricalRecommendationOutcomeCalculator,
)
from investment_terminal.history.historical_outcome_methodology_models import (
    HistoricalOutcomeMethodology,
)
from investment_terminal.history.historical_outcome_models import (
    HistoricalObservationWindow,
)
from investment_terminal.history.historical_outcome_price_evidence import (
    HistoricalOutcomePriceEvidenceProvider,
)
from investment_terminal.history.historical_outcome_query import (
    HistoricalOutcomeQuery,
    HistoricalOutcomeQueryService,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)
from investment_terminal.history.historical_outcome_source_import_quality import (
    HistoricalOutcomeSourceImportQualityService,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
)
from investment_terminal.history.historical_schema_migrations import (
    HISTORICAL_SCHEMA_MIGRATIONS,
    HISTORICAL_SCHEMA_TARGET_VERSION,
    HistoricalSchemaMigrator,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.history.historical_snapshot_repository import (
    HistoricalSnapshotRepository,
)
from investment_terminal.history.historical_sqlite_store import (
    HistoricalSQLiteStore,
)
from investment_terminal.history.historical_trading_session_window import (
    HistoricalTradingSessionWindowPolicy,
)
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import (
    CandleRepository,
)


WINDOW = HistoricalObservationWindow(
    kind="ELAPSED_DAYS",
    value=1,
)
METHODOLOGY = HistoricalOutcomeMethodology.sprint_14_exact_close_v1()
AS_OF = datetime(
    2026,
    8,
    12,
    12,
    0,
    tzinfo=timezone.utc,
)


def snapshot_id(sequence: int) -> str:
    return (
        f"11111111-1111-4111-8111-{sequence:012d}"
    )


def state(
    *,
    sequence: int,
    origin_at: datetime,
) -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=snapshot_id(sequence),
        generated_at=origin_at,
        recommendation_key="WORLD",
        present=True,
        symbol="IWDA",
        action="BUY",
        score=80.0,
        confidence=0.8,
    )


def snapshot(
    *,
    sequence: int,
    origin_at: datetime,
) -> HistoricalSnapshot:
    identifier = snapshot_id(sequence)
    return HistoricalSnapshot(
        snapshot_id=identifier,
        package_id=f"review-{sequence:03d}",
        package_schema_version="1.0",
        product_version="0.17.0",
        generated_at=origin_at,
        archived_at=origin_at + timedelta(
            minutes=1
        ),
        relative_path=(
            f"2026/08/{identifier}.json"
        ),
        checksum_sha256=(
            f"{sequence:x}" * 64
        )[:64],
        status="ARCHIVED",
    )


def save_close(
    repository: CandleRepository,
    *,
    timestamp: datetime,
    close: float,
) -> None:
    repository.save(
        Candle(
            symbol="IWDA",
            resolution="D",
            timestamp=timestamp,
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=1000.0,
            currency="EUR",
        )
    )


def observation_service(
    repository: CandleRepository,
) -> HistoricalMethodologyAwareObservationService:
    selection = HistoricalPriceEvidenceSelectionService(
        HistoricalOutcomePriceEvidenceProvider(
            repository
        )
    )
    methodology_evidence = HistoricalMethodologyAwarePriceEvidenceService(
        selection
    )
    unused_calendar = HistoricalLocalSessionCalendar(
        identity=HistoricalSessionCalendarIdentity(
            calendar_id="UNUSED",
            version=1,
            timezone="UTC",
            source="SPRINT_17_PROVENANCE_E2E_UNUSED",
        ),
        sessions=(),
    )
    return HistoricalMethodologyAwareObservationService(
        elapsed_window_policy=HistoricalObservationWindowPolicy(),
        trading_session_window_policy=HistoricalTradingSessionWindowPolicy(
            unused_calendar
        ),
        selection_service=selection,
        methodology_evidence_service=methodology_evidence,
        calculator=HistoricalRecommendationOutcomeCalculator(),
    )


def test_research_provenance_e2e_from_history_and_market_sqlite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history_path = tmp_path / "history.db"
    market_path = tmp_path / "market.db"

    origins = (
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    )

    history_store = HistoricalSQLiteStore(
        history_path
    )
    snapshot_repository = HistoricalSnapshotRepository(
        history_store
    )

    archived = tuple(
        snapshot(
            sequence=index,
            origin_at=origin,
        )
        for index, origin in enumerate(
            origins,
            start=1,
        )
    )
    for item in archived:
        snapshot_repository.add(
            item
        )

    HistoricalSchemaMigrator(
        store=history_store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    import_repository = HistoricalImportStateRepository(
        history_store
    )

    for index, item in enumerate(
        archived,
        start=1,
    ):
        base_time = item.archived_at + timedelta(
            minutes=1
        )
        import_repository.initialize_metadata(
            item,
            at=base_time,
        )

        # Two snapshots complete the canonical lifecycle; the third remains
        # metadata-only so import provenance is intentionally PARTIAL.
        if index <= 2:
            import_repository.mark_verified(
                item.snapshot_id,
                at=base_time + timedelta(
                    minutes=1
                ),
            )
            import_repository.mark_importing(
                item.snapshot_id,
                at=base_time + timedelta(
                    minutes=2
                ),
                importer_version="0.17.0",
            )
            import_repository.mark_imported(
                item.snapshot_id,
                at=base_time + timedelta(
                    minutes=3
                ),
            )

    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        market_path,
    )
    market_database = Database()
    market_database.initialize()
    candle_repository = CandleRepository(
        market_database
    )

    try:
        # All three source observations are calculable COMPLETE outcomes.
        for index, origin in enumerate(
            origins,
            start=1,
        ):
            save_close(
                candle_repository,
                timestamp=origin,
                close=100.0,
            )
            save_close(
                candle_repository,
                timestamp=origin + timedelta(
                    days=1
                ),
                close=100.0 + index,
            )

        observer = observation_service(
            candle_repository
        )
        source_results = tuple(
            observer.observe(
                state=state(
                    sequence=index,
                    origin_at=origin,
                ),
                window=WINDOW,
                methodology=METHODOLOGY,
                as_of=AS_OF,
                resolution="D",
            )
            for index, origin in enumerate(
                origins,
                start=1,
            )
        )

        assert tuple(
            result.observation.status
            for result in source_results
        ) == (
            "COMPLETE",
            "COMPLETE",
            "COMPLETE",
        )

        query = HistoricalOutcomeQuery(
            recommendation_key="WORLD",
            action="BUY",
            window_kind="ELAPSED_DAYS",
            window_value=1,
            methodology_id=METHODOLOGY.methodology_id,
            methodology_version=METHODOLOGY.version,
            origin_from=datetime(
                2026,
                8,
                2,
                12,
                0,
                tzinfo=timezone.utc,
            ),
            origin_to=datetime(
                2026,
                8,
                9,
                12,
                0,
                tzinfo=timezone.utc,
            ),
        )
        selected = HistoricalOutcomeQueryService().filter(
            source_results,
            query=query,
        )
        assert len(
            selected
        ) == 1
        assert selected[
            0
        ].observation.origin_at == origins[
            1
        ]

        import_quality = HistoricalOutcomeSourceImportQualityService(
            import_repository
        ).assess(
            source_results
        )

        research = HistoricalOutcomeResearchService().analyze(
            results=selected,
            protocol=HistoricalOutcomeResearchProtocol.descriptive_v1(
                allowed_methodology_identities=(
                    METHODOLOGY.identity_key,
                ),
                minimum_complete_sample_size=1,
            ),
            population_query=query,
            source_results=source_results,
            source_import_quality=import_quality,
        )

        assert len(
            research
        ) == 1
        cohort = research[
            0
        ]
        provenance = cohort.provenance

        assert provenance.complete_component_set is True
        assert provenance.available_components == (
            "SOURCE_IMPORT_QUALITY",
            "POPULATION_COMPLETENESS",
            "POPULATION_FRAME",
            "SELECTION_ACCOUNTING",
        )

        import_assessment = provenance.source_import_quality
        assert import_assessment is not None
        assert import_assessment.status == "PARTIAL"
        assert import_assessment.source_observation_count == 3
        assert import_assessment.unique_snapshot_count == 3
        assert import_assessment.imported_snapshot_count == 2
        assert import_assessment.non_imported_snapshot_count == 1
        assert import_assessment.missing_state_snapshot_count == 0
        assert import_assessment.imported_fraction == pytest.approx(
            2 / 3
        )
        assert dict(
            import_assessment.status_counts
        ) == {
            "METADATA_ONLY": 1,
            "IMPORTED": 2,
        }

        completeness = provenance.population_completeness
        assert completeness is not None
        assert completeness.status == "COVERED"
        assert completeness.observed_origin_start == origins[
            0
        ]
        assert completeness.observed_origin_end == origins[
            2
        ]
        assert completeness.covers_requested_start is True
        assert completeness.covers_requested_end is True
        assert completeness.internal_continuity_status == "NOT_ASSESSED"

        frame = provenance.population_frame
        assert frame.source_observation_count == 3
        assert frame.selected_candidate_count == 1
        assert frame.excluded_by_selection_count == 2
        assert frame.selection_fraction == pytest.approx(
            1 / 3
        )

        accounting = provenance.selection_accounting
        assert accounting is not None
        assert accounting.source_observation_count == 3
        assert accounting.selected_candidate_count == 1
        assert accounting.excluded_observation_count == 2
        assert {
            item.reason: item.count
            for item in accounting.reason_counts
        } == {
            "ORIGIN_FROM": 1,
            "ORIGIN_TO": 1,
        }
        assert accounting.total_reason_failures == 2

        assert cohort.coverage.candidate_count == 1
        assert cohort.coverage.eligible_count == 1
        assert cohort.coverage.complete_count == 1
        assert cohort.coverage.excluded_count == 0
        assert cohort.sample_assessment.status == "SUFFICIENT"

        summary = cohort.descriptive_summary
        assert summary is not None
        assert summary.count == 1
        assert summary.mean_price_change_fraction == pytest.approx(
            0.02
        )

        assert cohort.claim_assessment.claim_policy == "DESCRIPTIVE_ONLY"
        assert cohort.claim_assessment.descriptive_claims_allowed is True
        assert cohort.claim_assessment.predictive_claims_allowed is False
        assert cohort.claim_assessment.causal_claims_allowed is False
        assert cohort.claim_assessment.effectiveness_claims_allowed is False

        payload = cohort.to_dict()

        # Canonical provenance envelope.
        assert payload["provenance"]["complete_component_set"] is True
        assert payload["provenance"]["source_import_quality"]["status"] == (
            "PARTIAL"
        )
        assert payload["provenance"]["population_completeness"]["status"] == (
            "COVERED"
        )
        assert payload["provenance"]["population_frame"][
            "source_observation_count"
        ] == 3
        assert payload["provenance"]["selection_accounting"][
            "excluded_observation_count"
        ] == 2

        # Transitional aliases remain consistent during the migration window.
        assert payload["population_frame"] == payload["provenance"][
            "population_frame"
        ]
        assert payload["selection_accounting"] == payload["provenance"][
            "selection_accounting"
        ]
        assert payload["population_completeness"] == payload["provenance"][
            "population_completeness"
        ]
        assert payload["source_import_quality"] == payload["provenance"][
            "source_import_quality"
        ]
    finally:
        market_database.close()

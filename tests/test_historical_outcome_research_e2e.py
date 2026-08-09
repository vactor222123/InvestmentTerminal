"""
Deterministic multi-observation end-to-end fixture for Sprint 16 research.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sqlite3

import pytest

from investment_terminal.config.settings import Settings
from investment_terminal.database.database import Database
from investment_terminal.history.historical_evidence_selection import (
    HistoricalPriceEvidenceSelectionService,
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
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.history.historical_outcome_research_service import (
    HistoricalOutcomeResearchService,
)
from investment_terminal.history.historical_recommendation_transition_models import (
    HistoricalRecommendationState,
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
    10,
    12,
    0,
    tzinfo=timezone.utc,
)


def state(
    *,
    sequence: int,
    origin_at: datetime,
) -> HistoricalRecommendationState:
    return HistoricalRecommendationState(
        snapshot_id=(
            f"11111111-1111-4111-8111-{sequence:012d}"
        ),
        generated_at=origin_at,
        recommendation_key="WORLD",
        present=True,
        symbol="IWDA",
        action="BUY",
        score=80.0,
        confidence=0.8,
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
    *,
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
            source="SPRINT_16_E2E_UNUSED",
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


def test_multi_observation_research_e2e(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_path = tmp_path / "market.db"
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        market_path,
    )

    database = Database()
    database.initialize()
    repository = CandleRepository(
        database
    )

    # Keep origins separated so no observation endpoint timestamp overlaps
    # another observation origin timestamp.
    origins = (
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc),
    )
    states = tuple(
        state(
            sequence=index,
            origin_at=origin,
        )
        for index, origin in enumerate(
            origins,
            start=1,
        )
    )

    try:
        # COMPLETE +10%
        save_close(
            repository,
            timestamp=origins[0],
            close=100.0,
        )
        save_close(
            repository,
            timestamp=origins[0] + timedelta(days=1),
            close=110.0,
        )

        # COMPLETE -5%
        save_close(
            repository,
            timestamp=origins[1],
            close=100.0,
        )
        save_close(
            repository,
            timestamp=origins[1] + timedelta(days=1),
            close=95.0,
        )

        # COMPLETE flat
        save_close(
            repository,
            timestamp=origins[2],
            close=100.0,
        )
        save_close(
            repository,
            timestamp=origins[2] + timedelta(days=1),
            close=100.0,
        )

        # PARTIAL: origin exists, exact endpoint intentionally absent.
        save_close(
            repository,
            timestamp=origins[3],
            close=100.0,
        )

        # NOT_MATURE: origin exists, endpoint is after AS_OF.
        save_close(
            repository,
            timestamp=origins[4],
            close=100.0,
        )

        service = observation_service(
            repository=repository
        )
        results = tuple(
            service.observe(
                state=item,
                window=WINDOW,
                methodology=METHODOLOGY,
                as_of=AS_OF,
                resolution="D",
            )
            for item in states
        )

        assert tuple(
            result.observation.status
            for result in results
        ) == (
            "COMPLETE",
            "COMPLETE",
            "COMPLETE",
            "PARTIAL",
            "NOT_MATURE",
        )

        protocol = HistoricalOutcomeResearchProtocol.descriptive_v1(
            allowed_methodology_identities=(
                METHODOLOGY.identity_key,
            ),
            minimum_complete_sample_size=3,
        )
        query = HistoricalOutcomeQuery(
            recommendation_key="WORLD",
            action="BUY",
            window_kind="ELAPSED_DAYS",
            window_value=1,
            methodology_id=METHODOLOGY.methodology_id,
            methodology_version=METHODOLOGY.version,
        )

        research = HistoricalOutcomeResearchService().analyze(
            results=results,
            protocol=protocol,
            population_query=query,
        )

        assert len(research) == 1
        cohort = research[0]

        assert cohort.protocol_identity == (
            "DESCRIPTIVE_OUTCOME_RESEARCH@1"
        )
        assert cohort.cohort.value_for(
            "METHODOLOGY_IDENTITY"
        ) == "ELAPSED_DAYS_EXACT_CLOSE@1"
        assert cohort.cohort.value_for(
            "WINDOW_VALUE"
        ) == "1"

        assert cohort.population.candidate_count == 5
        assert cohort.population.prefiltered is True
        assert cohort.population.requested_action == "BUY"
        assert any(
            "not automatically an unbiased" in warning
            for warning in cohort.population.warnings
        )

        assert cohort.coverage.candidate_count == 5
        assert cohort.coverage.eligible_count == 3
        assert cohort.coverage.complete_count == 3
        assert cohort.coverage.partial_count == 1
        assert cohort.coverage.not_mature_count == 1
        assert cohort.coverage.unavailable_count == 0
        assert cohort.coverage.excluded_count == 2
        assert cohort.coverage.coverage_fraction == pytest.approx(
            3 / 5
        )

        assert cohort.sample_assessment.status == "SUFFICIENT"
        assert cohort.sample_assessment.eligible_sample_size == 3
        assert cohort.sample_assessment.minimum_required_sample_size == 3
        assert cohort.sample_assessment.shortfall == 0

        summary = cohort.descriptive_summary
        assert summary is not None
        assert summary.count == 3
        assert summary.mean_price_change_fraction == pytest.approx(
            (
                (110.0 / 100.0 - 1.0)
                + (95.0 / 100.0 - 1.0)
                + (100.0 / 100.0 - 1.0)
            )
            / 3
        )
        assert summary.median_price_change_fraction == pytest.approx(
            0.0
        )
        assert summary.minimum_price_change_fraction == pytest.approx(
            -0.05
        )
        assert summary.maximum_price_change_fraction == pytest.approx(
            0.10
        )
        assert summary.positive_movement_count == 1
        assert summary.negative_movement_count == 1
        assert summary.zero_movement_count == 1

        uncertainty = cohort.uncertainty
        assert uncertainty is not None
        assert uncertainty.sample_size == 3
        assert uncertainty.sample_standard_deviation is not None
        assert uncertainty.standard_error_of_mean is not None
        assert uncertainty.confidence_interval_method is None
        assert uncertainty.confidence_level is None

        claims = cohort.claim_assessment
        assert claims.claim_policy == "DESCRIPTIVE_ONLY"
        assert claims.descriptive_claims_allowed is True
        assert claims.predictive_claims_allowed is False
        assert claims.causal_claims_allowed is False
        assert claims.effectiveness_claims_allowed is False

        payload = cohort.to_dict()
        encoded = json.dumps(
            payload,
            allow_nan=False,
            sort_keys=True,
        )
        decoded = json.loads(
            encoded
        )

        assert decoded[
            "coverage"
        ][
            "candidate_count"
        ] == 5
        assert decoded[
            "sample_assessment"
        ][
            "status"
        ] == "SUFFICIENT"
        assert decoded[
            "claim_assessment"
        ][
            "effectiveness_claims_allowed"
        ] is False
    finally:
        database.close()

    # Sprint 16 research remains derived/on demand: no outcome/research table.
    with sqlite3.connect(
        market_path
    ) as connection:
        table_names = {
            row[0].lower()
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert not any(
        "research" in name
        or "outcome" in name
        for name in table_names
    )


def test_multi_observation_research_threshold_can_withhold_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_path = tmp_path / "market.db"
    monkeypatch.setattr(
        Settings,
        "DATABASE_PATH",
        market_path,
    )

    database = Database()
    database.initialize()
    repository = CandleRepository(
        database
    )

    origins = (
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
    )

    try:
        for index, origin in enumerate(
            origins,
            start=1,
        ):
            save_close(
                repository,
                timestamp=origin,
                close=100.0,
            )
            save_close(
                repository,
                timestamp=origin + timedelta(days=1),
                close=100.0 + index,
            )

        service = observation_service(
            repository=repository
        )
        results = tuple(
            service.observe(
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

        research = HistoricalOutcomeResearchService().analyze(
            results=results,
            protocol=HistoricalOutcomeResearchProtocol.descriptive_v1(
                allowed_methodology_identities=(
                    METHODOLOGY.identity_key,
                ),
                minimum_complete_sample_size=3,
            ),
            population_query=HistoricalOutcomeQuery(
                recommendation_key="WORLD",
                window_kind="ELAPSED_DAYS",
                window_value=1,
                methodology_id=METHODOLOGY.methodology_id,
                methodology_version=METHODOLOGY.version,
            ),
        )

        cohort = research[0]

        assert cohort.coverage.eligible_count == 2
        assert cohort.sample_assessment.status == "INSUFFICIENT"
        assert cohort.sample_assessment.shortfall == 1
        assert cohort.descriptive_summary is not None
        assert cohort.uncertainty is not None
        assert (
            cohort.claim_assessment.descriptive_claims_allowed
            is False
        )
        assert (
            cohort.claim_assessment.effectiveness_claims_allowed
            is False
        )
    finally:
        database.close()

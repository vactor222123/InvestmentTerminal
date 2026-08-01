"""
Tests for portfolio ranking models.
"""

import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.decision_engine.decision_engine import (
    DecisionEngine,
)
from investment_terminal.portfolio.ranking_models import (
    RankingCandidate,
    RankingResult,
)
from tests.test_analysis_exporter import (
    create_fundamental_score,
    create_fundamental_snapshot,
    create_technical_analysis,
    create_technical_score,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def create_decision(
    symbol: str = "MSFT",
):
    return DecisionEngine().evaluate(
        technical_analysis=(
            create_technical_analysis(
                symbol=symbol
            )
        ),
        technical_score=(
            create_technical_score(
                symbol=symbol
            )
        ),
        fundamental_snapshot=(
            create_fundamental_snapshot(
                symbol=symbol
            )
        ),
        fundamental_score=(
            create_fundamental_score(
                symbol=symbol
            )
        ),
        generated_at=GENERATED_AT,
    )


def create_candidate(
    rank: int = 1,
    symbol: str = "MSFT",
) -> RankingCandidate:
    return RankingCandidate(
        rank=rank,
        decision=create_decision(symbol),
    )


def test_candidate_exposes_decision_values() -> None:
    candidate = create_candidate()

    assert candidate.rank == 1
    assert candidate.symbol == "MSFT"
    assert candidate.currency == "USD"
    assert candidate.overall_score == pytest.approx(
        77.41
    )
    assert candidate.confidence_score == pytest.approx(
        96.72
    )
    assert candidate.fundamental_score == 85.68
    assert candidate.technical_score == 65.0
    assert candidate.classification == "STRONG"
    assert (
        candidate.business_quality
        == "EXCELLENT"
    )
    assert candidate.risk_level == "MEDIUM"


@pytest.mark.parametrize(
    "rank",
    [
        0,
        -1,
        1.5,
        True,
    ],
)
def test_candidate_rejects_invalid_rank(
    rank,
) -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        RankingCandidate(
            rank=rank,
            decision=create_decision(),
        )


def test_candidate_rejects_invalid_decision() -> None:
    with pytest.raises(
        TypeError,
        match="DecisionResult",
    ):
        RankingCandidate(
            rank=1,
            decision=None,
        )


def test_ranking_result_calculates_properties() -> None:
    result = RankingResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        candidates=(
            create_candidate(
                rank=1,
                symbol="MSFT",
            ),
            create_candidate(
                rank=2,
                symbol="AAPL",
            ),
            create_candidate(
                rank=3,
                symbol="GOOGL",
            ),
        ),
    )

    assert result.universe_size == 3
    assert result.top_candidate.symbol == "MSFT"


def test_ranking_result_requires_consecutive_ranks() -> None:
    with pytest.raises(
        ValueError,
        match="consecutive",
    ):
        RankingResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            candidates=(
                create_candidate(
                    rank=1,
                    symbol="MSFT",
                ),
                create_candidate(
                    rank=3,
                    symbol="AAPL",
                ),
            ),
        )


def test_ranking_result_rejects_duplicate_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="unique symbols",
    ):
        RankingResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            candidates=(
                create_candidate(
                    rank=1,
                    symbol="MSFT",
                ),
                create_candidate(
                    rank=2,
                    symbol="MSFT",
                ),
            ),
        )


def test_ranking_result_rejects_empty_candidates() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        RankingResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            candidates=(),
        )


def test_ranking_result_is_json_serializable() -> None:
    result = RankingResult(
        schema_version="1.0",
        generated_at=GENERATED_AT,
        candidates=(
            create_candidate(
                rank=1,
                symbol="MSFT",
            ),
            create_candidate(
                rank=2,
                symbol="AAPL",
            ),
        ),
    )

    payload = result.to_dict()

    serialized = json.dumps(
        payload,
        allow_nan=False,
    )

    assert '"top_symbol": "MSFT"' in serialized
    assert payload["universe_size"] == 2
    assert isinstance(
        payload["candidates"],
        list,
    )
    assert (
        payload["candidates"][0]
        ["decision"]
        ["classification"]
        == "STRONG"
    )


def test_schema_version_is_normalized() -> None:
    result = RankingResult(
        schema_version=" 1.0 ",
        generated_at=GENERATED_AT,
        candidates=(
            create_candidate(),
        ),
    )

    assert result.schema_version == "1.0"


def test_result_rejects_non_tuple_candidates() -> None:
    with pytest.raises(
        TypeError,
        match="candidates must be a tuple",
    ):
        RankingResult(
            schema_version="1.0",
            generated_at=GENERATED_AT,
            candidates=[
                create_candidate(),
            ],
        )
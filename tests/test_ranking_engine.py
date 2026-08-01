"""
Tests for RankingEngine.
"""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from investment_terminal.decision_engine.decision_model import (
    DecisionConfidence,
    DecisionResult,
    DecisionScoreSummary,
)
from investment_terminal.portfolio.ranking_engine import (
    RankingEngine,
)
from tests.test_ranking_models import (
    create_decision,
)


GENERATED_AT = datetime(
    2026,
    8,
    1,
    12,
    0,
    tzinfo=timezone.utc,
)


def modify_decision(
    decision: DecisionResult,
    *,
    technical: float | None = None,
    fundamental: float | None = None,
    overall: float | None = None,
    confidence: float | None = None,
) -> DecisionResult:
    scores = replace(
        decision.scores,
        technical=(
            decision.scores.technical
            if technical is None
            else technical
        ),
        fundamental=(
            decision.scores.fundamental
            if fundamental is None
            else fundamental
        ),
        overall=(
            decision.scores.overall
            if overall is None
            else overall
        ),
    )

    confidence_result = replace(
        decision.confidence,
        score=(
            decision.confidence.score
            if confidence is None
            else confidence
        ),
    )

    return replace(
        decision,
        scores=scores,
        confidence=confidence_result,
    )


def test_rank_orders_by_overall_score() -> None:
    msft = modify_decision(
        create_decision("MSFT"),
        overall=80.0,
    )
    aapl = modify_decision(
        create_decision("AAPL"),
        overall=70.0,
    )
    googl = modify_decision(
        create_decision("GOOGL"),
        overall=75.0,
    )

    result = RankingEngine().rank(
        decisions=[
            aapl,
            msft,
            googl,
        ],
        generated_at=GENERATED_AT,
    )

    assert [
        candidate.symbol
        for candidate in result.candidates
    ] == [
        "MSFT",
        "GOOGL",
        "AAPL",
    ]

    assert [
        candidate.rank
        for candidate in result.candidates
    ] == [
        1,
        2,
        3,
    ]


def test_rank_uses_confidence_as_tiebreaker() -> None:
    msft = modify_decision(
        create_decision("MSFT"),
        overall=75.0,
        confidence=90.0,
    )
    aapl = modify_decision(
        create_decision("AAPL"),
        overall=75.0,
        confidence=95.0,
    )

    result = RankingEngine().rank(
        [msft, aapl],
        generated_at=GENERATED_AT,
    )

    assert result.top_candidate.symbol == "AAPL"


def test_rank_uses_fundamental_as_tiebreaker() -> None:
    msft = modify_decision(
        create_decision("MSFT"),
        overall=75.0,
        confidence=95.0,
        fundamental=80.0,
    )
    aapl = modify_decision(
        create_decision("AAPL"),
        overall=75.0,
        confidence=95.0,
        fundamental=85.0,
    )

    result = RankingEngine().rank(
        [msft, aapl],
        generated_at=GENERATED_AT,
    )

    assert result.top_candidate.symbol == "AAPL"


def test_rank_uses_technical_as_tiebreaker() -> None:
    msft = modify_decision(
        create_decision("MSFT"),
        overall=75.0,
        confidence=95.0,
        fundamental=85.0,
        technical=70.0,
    )
    aapl = modify_decision(
        create_decision("AAPL"),
        overall=75.0,
        confidence=95.0,
        fundamental=85.0,
        technical=65.0,
    )

    result = RankingEngine().rank(
        [aapl, msft],
        generated_at=GENERATED_AT,
    )

    assert result.top_candidate.symbol == "MSFT"


def test_rank_uses_symbol_as_final_tiebreaker() -> None:
    msft = modify_decision(
        create_decision("MSFT"),
        overall=75.0,
        confidence=95.0,
        fundamental=85.0,
        technical=70.0,
    )
    aapl = modify_decision(
        create_decision("AAPL"),
        overall=75.0,
        confidence=95.0,
        fundamental=85.0,
        technical=70.0,
    )

    result = RankingEngine().rank(
        [msft, aapl],
        generated_at=GENERATED_AT,
    )

    assert [
        candidate.symbol
        for candidate in result.candidates
    ] == [
        "AAPL",
        "MSFT",
    ]


def test_rank_does_not_modify_input_order() -> None:
    decisions = [
        modify_decision(
            create_decision("AAPL"),
            overall=70.0,
        ),
        modify_decision(
            create_decision("MSFT"),
            overall=80.0,
        ),
    ]

    RankingEngine().rank(
        decisions,
        generated_at=GENERATED_AT,
    )

    assert [
        decision.symbol
        for decision in decisions
    ] == [
        "AAPL",
        "MSFT",
    ]


def test_rank_uses_generated_at() -> None:
    result = RankingEngine().rank(
        [create_decision()],
        generated_at=GENERATED_AT,
    )

    assert result.generated_at == GENERATED_AT
    assert result.schema_version == "1.0"


@pytest.mark.parametrize(
    "decisions",
    [
        [],
        (),
    ],
)
def test_rank_rejects_empty_decisions(
    decisions,
) -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        RankingEngine().rank(decisions)


@pytest.mark.parametrize(
    "decisions",
    [
        "MSFT",
        {"MSFT"},
        None,
    ],
)
def test_rank_rejects_invalid_collection(
    decisions,
) -> None:
    with pytest.raises(
        TypeError,
        match="list or tuple",
    ):
        RankingEngine().rank(decisions)


def test_rank_rejects_invalid_decision_item() -> None:
    with pytest.raises(
        TypeError,
        match="DecisionResult",
    ):
        RankingEngine().rank(
            [
                create_decision(),
                None,
            ]
        )


def test_rank_rejects_duplicate_symbols() -> None:
    with pytest.raises(
        ValueError,
        match="unique symbols",
    ):
        RankingEngine().rank(
            [
                create_decision("MSFT"),
                create_decision("MSFT"),
            ]
        )


def test_rank_rejects_invalid_generated_at() -> None:
    with pytest.raises(
        TypeError,
        match="generated_at",
    ):
        RankingEngine().rank(
            [create_decision()],
            generated_at="2026-08-01",
        )
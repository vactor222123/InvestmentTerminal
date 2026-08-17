"""Tests for append-only portfolio valuation-history repositories."""

from datetime import datetime, timezone

import pytest

from investment_terminal.portfolio.portfolio_valuation_history import (
    PortfolioValuationSnapshot,
)
from investment_terminal.portfolio.portfolio_valuation_history_repository import (
    InMemoryPortfolioValuationHistoryRepository,
    PortfolioValuationHistoryRepository,
)
from investment_terminal.portfolio.realized_performance import (
    RealizedPerformance,
)
from investment_terminal.portfolio.unrealized_performance import (
    UnrealizedPerformance,
)


def timestamp(day: int) -> datetime:
    return datetime(2026, 8, day, 12, tzinfo=timezone.utc)


def valuation(
    snapshot_id: str,
    day: int,
    *,
    ledger_id: str = "main",
    portfolio_name: str = "Personal",
) -> PortfolioValuationSnapshot:
    return PortfolioValuationSnapshot.build(
        snapshot_id=snapshot_id,
        unrealized=UnrealizedPerformance(
            ledger_id=ledger_id,
            portfolio_name=portfolio_name,
            valued_at=timestamp(day),
            positions=(),
            currency_summaries=(),
        ),
        realized=RealizedPerformance(
            ledger_id=ledger_id,
            portfolio_name=portfolio_name,
            sales=(),
            currency_summaries=(),
        ),
    )


def repository() -> InMemoryPortfolioValuationHistoryRepository:
    result = InMemoryPortfolioValuationHistoryRepository(
        ledger_id="main",
        portfolio_name="Personal",
    )
    assert isinstance(result, PortfolioValuationHistoryRepository)
    return result


def test_add_get_and_require_exact_snapshot() -> None:
    repo = repository()
    expected = valuation("valuation-1", 1)

    assert repo.add(expected) is expected
    assert repo.get(" valuation-1 ") is expected
    assert repo.require("valuation-1") is expected
    assert repo.get("missing") is None


def test_require_reports_missing_snapshot() -> None:
    with pytest.raises(KeyError, match="No portfolio valuation snapshot"):
        repository().require("missing")


def test_duplicate_identity_is_rejected_and_original_is_preserved() -> None:
    repo = repository()
    original = valuation("valuation-1", 1)
    repo.add(original)

    with pytest.raises(ValueError, match="identity already exists"):
        repo.add(valuation("valuation-1", 2))

    assert repo.require("valuation-1") is original


def test_add_rejects_wrong_type_or_repository_ownership() -> None:
    repo = repository()
    with pytest.raises(TypeError, match="PortfolioValuationSnapshot"):
        repo.add(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="repository ledger_id"):
        repo.add(valuation("other-ledger", 1, ledger_id="other"))
    with pytest.raises(ValueError, match="repository portfolio_name"):
        repo.add(valuation("other-portfolio", 1, portfolio_name="Other"))


def test_list_all_is_deterministic_independent_of_insertion_order() -> None:
    repo = repository()
    later_b = valuation("valuation-b", 2)
    earlier = valuation("valuation-z", 1)
    later_a = valuation("valuation-a", 2)
    for item in (later_b, earlier, later_a):
        repo.add(item)

    assert repo.list_all() == (earlier, later_a, later_b)


def test_list_between_uses_half_open_interval() -> None:
    repo = repository()
    first = valuation("valuation-1", 1)
    second = valuation("valuation-2", 2)
    third = valuation("valuation-3", 3)
    for item in (first, second, third):
        repo.add(item)

    assert repo.list_between(timestamp(1), timestamp(3)) == (first, second)
    with pytest.raises(ValueError, match="timezone-aware"):
        repo.list_between(datetime(2026, 8, 1), timestamp(2))
    with pytest.raises(ValueError, match="later than"):
        repo.list_between(timestamp(2), timestamp(1))


def test_recent_and_latest_preserve_chronological_order() -> None:
    repo = repository()
    values = tuple(valuation(f"valuation-{day}", day) for day in (1, 2, 3))
    for item in values:
        repo.add(item)

    assert repo.list_recent(2) == values[1:]
    assert repo.latest() is values[-1]
    with pytest.raises(ValueError, match="greater than zero"):
        repo.list_recent(0)
    with pytest.raises(TypeError, match="integer"):
        repo.list_recent(True)


def test_history_returns_immutable_repository_projection() -> None:
    repo = repository()
    second = valuation("valuation-2", 2)
    first = valuation("valuation-1", 1)
    repo.add(second)
    repo.add(first)

    history = repo.history()

    assert history.ledger_id == "main"
    assert history.portfolio_name == "Personal"
    assert history.snapshots == (first, second)


def test_empty_repository_has_no_latest_snapshot() -> None:
    repo = repository()

    assert repo.latest() is None
    assert repo.list_all() == ()
    assert repo.history().snapshots == ()

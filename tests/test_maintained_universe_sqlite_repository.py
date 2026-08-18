"""Tests for durable SQLite maintained-universe persistence."""

from pathlib import Path

import pytest

from investment_terminal.universe.maintained_universe_repository import (
    MaintainedAssetUniverseRepository,
)
from investment_terminal.universe.maintained_universe_sqlite_repository import (
    SQLiteMaintainedAssetUniverseRepository,
)
from investment_terminal.universe.maintained_universe_sqlite_store import (
    MaintainedAssetUniverseSQLiteStore,
)
from tests.test_maintained_universe_repository import (
    evidence,
    instrument,
    timestamp,
)


def store(path: Path) -> MaintainedAssetUniverseSQLiteStore:
    return MaintainedAssetUniverseSQLiteStore(path)


def repository(path: Path) -> SQLiteMaintainedAssetUniverseRepository:
    value = SQLiteMaintainedAssetUniverseRepository(store(path))
    assert isinstance(value, MaintainedAssetUniverseRepository)
    return value


def test_store_initializes_versioned_schema(tmp_path: Path) -> None:
    value = store(tmp_path / "nested" / "universes.db")
    assert value.initialize().exists()
    assert value.schema_version() == 1


def test_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    value = store(tmp_path / "universes.db")
    with pytest.raises(RuntimeError):
        with value.transaction() as connection:
            connection.execute(
                "INSERT INTO maintained_universe_evidence "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "TEST@1",
                    "TEST",
                    1,
                    timestamp(1).isoformat(),
                    "TEST",
                    "record-1",
                    "{}",
                ),
            )
            raise RuntimeError("interrupt")
    with value.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM maintained_universe_evidence"
        ).fetchone()[0]
    assert count == 0


def test_round_trip_survives_restart_and_preserves_queries(
    tmp_path: Path,
) -> None:
    database = tmp_path / "universes.db"
    first = evidence(
        "US_LARGE_CAP",
        1,
        10,
        instruments=(instrument("MSFT"), instrument("AAPL")),
    )
    second = evidence(
        "GLOBAL_EQUITY",
        1,
        11,
        instruments=(instrument("AAPL"),),
    )
    third = evidence("US_LARGE_CAP", 2, 12)
    original = repository(database)
    for item in (third, first, second):
        original.add(item)

    restarted = repository(database)
    assert restarted.list_all() == (first, second, third)
    assert restarted.require("US_LARGE_CAP@1").to_dict() == first.to_dict()
    assert restarted.list_between(timestamp(10), timestamp(12)) == (
        first,
        second,
    )
    assert restarted.list_for_universe("us_large_cap") == (first, third)
    assert restarted.list_for_instrument("xnas:aapl") == (first, second)
    assert restarted.latest("US_LARGE_CAP") == third
    assert restarted.latest("MISSING") is None


def test_duplicate_universe_and_source_identities_are_rejected(
    tmp_path: Path,
) -> None:
    repo = repository(tmp_path / "universes.db")
    original = evidence("US_LARGE_CAP", 1, 10)
    repo.add(original)

    with pytest.raises(ValueError, match="identity already exists"):
        repo.add(evidence("US_LARGE_CAP", 1, 11))
    with pytest.raises(ValueError, match="identity already exists"):
        repo.add(evidence(
            "GLOBAL_EQUITY",
            1,
            11,
            source_record_id="US_LARGE_CAP-1",
        ))
    assert repo.require("US_LARGE_CAP@1") == original


def test_corrupt_payload_fails_visible_on_read(tmp_path: Path) -> None:
    value = store(tmp_path / "universes.db")
    value.initialize()
    with value.transaction() as connection:
        connection.execute(
            "INSERT INTO maintained_universe_evidence "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "BAD@1",
                "BAD",
                1,
                timestamp(1).isoformat(),
                "TEST",
                "bad-1",
                "not-json",
            ),
        )
    with pytest.raises(Exception):
        repository(value.database_path).require("BAD@1")


def test_store_rejects_invalid_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="database_path"):
        store(tmp_path / "universes.txt")

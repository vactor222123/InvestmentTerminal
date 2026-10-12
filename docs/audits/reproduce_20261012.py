"""Audit characterization only: assertions reproduce defects at 53fd2be.

Run from the repository: python docs/audits/reproduce_20261012.py
Uses only in-memory SQLite and an automatically removed temporary directory.
No provider calls or private runtime files. After repairs these assertions should
fail: this is evidence, NOT a regression suite defining desired behavior.
"""

import sqlite3
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from investment_terminal.cli.weekly_candle_refresh import main as weekly
from investment_terminal.database.schema import SCHEMA
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import CandleRepository


def setup():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection, CandleRepository(SimpleNamespace(connection=connection))


def main():
    base = Candle(
        symbol="SYNTH", resolution="D",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open_price=10, high_price=12, low_price=9, close_price=11,
        volume=100, currency="USD",
    )
    connection, repository = setup()
    try:
        assert repository.save_many([base]) == 1
        assert repository.save_many([replace(base, close_price=10, currency="EUR")]) == 0
        assert repository.get_latest("SYNTH", "D").currency == "USD"
        print("A01 CONFLICT_SILENTLY_IGNORED: reproduced")
    finally:
        connection.close()

    connection, repository = setup()
    try:
        repository.save_many([
            base,
            replace(base, timestamp=base.timestamp.astimezone(timezone(timedelta(hours=1)))),
        ])
        assert repository.count("SYNTH", "D") == 2
        repository.save(replace(base, timestamp=datetime(2026, 1, 2)))
        assert repository.count("SYNTH", "D") == 3
        print("A02 SAME_INSTANT_DUPLICATED_AND_NAIVE_ACCEPTED: reproduced")
    finally:
        connection.close()

    connection, repository = setup()
    try:
        repository.save(replace(base, currency="GBp"))
        assert repository.get_latest("SYNTH", "D").currency == "GBP"
        print("A03 GBP_MINOR_UNIT_COLLAPSED: reproduced")
    finally:
        connection.close()

    connection, repository = setup()
    try:
        connection.execute(
            "CREATE TRIGGER fail_second BEFORE INSERT ON candles "
            "WHEN NEW.symbol = 'FAIL' BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"
        )
        try:
            repository.save_many([base, replace(base, symbol="FAIL")])
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Expected trigger failure")
        assert connection.in_transaction and repository.count("SYNTH", "D") == 1
        repository.save(replace(base, symbol="LATER"))
        assert not connection.in_transaction and repository.count("SYNTH", "D") == 1
        print("A04 FAILED_BATCH_PREFIX_COMMITTED_BY_LATER_SAVE: reproduced")
    finally:
        connection.close()

    with TemporaryDirectory(prefix="terminal-audit-") as temporary:
        root = Path(temporary)
        source = root / "manifest.json"
        source.write_bytes(b'{"original":true}')
        code = weekly([
            "--manifest", str(source), "--manifest-checksum", "0" * 64,
            "--source-checkpoint-directory", str(root / "source"),
            "--weekly-checkpoint", str(root / "weekly.json"),
            "--database", str(root / "missing.db"),
            "--cache-directory", str(root / "cache"),
            "--report-output", str(source),
            "--end", "2026-01-02T00:00:00+00:00", "--max-items", "1",
        ], client=object(), clock=lambda: datetime(2026, 1, 3, tzinfo=timezone.utc))
        assert code == 1 and b"PRECONDITION_OR_RUNTIME_FAILURE" in source.read_bytes()
        print("A05 PREFLIGHT_FAILURE_OVERWRITES_ALIASED_INPUT: reproduced")


if __name__ == "__main__":
    main()

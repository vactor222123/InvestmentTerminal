"""Tests for explicit calendar coverage CLI."""

import json
import hashlib
from pathlib import Path

from investment_terminal.cli.candle_coverage_quality import main
from investment_terminal.database.database import Database
from investment_terminal.models.candle import Candle
from investment_terminal.repositories.candle_repository import CandleRepository
from datetime import datetime, timezone


def test_cli_writes_complete_report(tmp_path: Path) -> None:
    database_path = tmp_path / "market.db"
    database = Database(database_path)
    database.initialize()
    CandleRepository(database).save(Candle(
        symbol="MSFT", resolution="D",
        timestamp=datetime(2026, 8, 3, 4, tzinfo=timezone.utc),
        open_price=100, high_price=102, low_price=99, close_price=101,
        volume=1000, currency="USD",
    ))
    database.close()
    calendar_path = tmp_path / "calendar.json"
    sessions = [{"session_key": "XNAS:2026-08-03",
                 "session_date": "2026-08-03",
                 "opens_at": "2026-08-03T09:30:00-04:00",
                 "closes_at": "2026-08-03T16:00:00-04:00"}]
    digest = hashlib.sha256(json.dumps(
        sessions, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    calendar_path.write_text(json.dumps({
        "calendar": {"calendar_id": "XNAS", "version": 1,
                     "timezone": "America/New_York", "source": "FIXTURE"},
        "evidence": {"source_uri": "https://example.test/calendar",
                     "retrieved_at": "2026-08-19T00:00:00+00:00",
                     "sessions_sha256": digest},
        "sessions": sessions,
    }), encoding="utf-8")
    output = tmp_path / "report.json"
    assert main(["--database", str(database_path), "--session-calendar",
                 str(calendar_path), "--symbol", "MSFT", "--start",
                 "2026-08-03T00:00:00+00:00", "--end",
                 "2026-08-04T00:00:00+00:00", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["calendar_identity"] == "XNAS@1"
    assert payload["is_complete"] is True
    assert payload["calendar_evidence"]["sessions_sha256"] == digest

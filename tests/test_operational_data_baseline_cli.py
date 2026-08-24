"""CLI tests for operational data baseline export."""

import json
from pathlib import Path

from investment_terminal.cli.operational_data_baseline import main


def test_cli_prints_machine_readable_report(capsys) -> None:
    main(["--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["refresh_observability"] == "UNMEASURED"


def test_cli_atomically_exports_complete_report(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "baseline.json"
    main(["--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert len(payload["stores"]) == 8


def test_cli_conditionally_projects_explicit_refresh_report(tmp_path: Path) -> None:
    refresh = tmp_path / "refresh.json"
    refresh.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provider_identity": "YAHOO_FINANCE",
                "status": "FAILED",
                "request": {
                    "symbol": "MSFT",
                    "resolution": "D",
                    "currency": "USD",
                    "checked_at": "2026-08-24T22:00:00+00:00",
                },
                "database": "private.db",
                "started_at": "2026-08-24T22:00:01+00:00",
                "completed_at": "2026-08-24T22:00:02+00:00",
                "duration_seconds": 1.0,
                "result": None,
                "failure": {"type": "RuntimeError", "reason": "unavailable"},
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "baseline.json"

    main(["--refresh-report", str(refresh), "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert len(payload["stores"]) == 9
    refresh_store = next(
        store for store in payload["stores"]
        if store["store_identity"] == "REFRESH_REPORT"
    )
    assert refresh_store["state"] == "READY"
    assert "private.db" not in json.dumps(refresh_store)

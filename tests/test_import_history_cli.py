"""
Tests for the History import CLI.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.import_history import (
    main,
)
from investment_terminal.history.historical_snapshot_manifest import (
    HistoricalSnapshotManifest,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
RELATIVE_PATH = "2026/08/review.json"


def package_payload() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": (
            "2026-08-03T17:35:00+00:00"
        ),
        "sections": {
            "portfolio": {
                "status": "COST_BASIS_ONLY",
                "cost_basis_snapshot": {
                    "portfolio_name": "Test Portfolio",
                    "base_currency": "EUR",
                    "total_value": 10000.0,
                    "invested_value": 8500.0,
                    "cash_value": 1500.0,
                    "monthly_contribution": 1200.0,
                },
                "market_value": None,
            },
            "machine_recommendations": {
                "status": "CONNECTED",
                "recommendations": {
                    "items": [
                        {
                            "symbol": "BABA",
                            "recommendation": "BUY",
                            "score": 82.5,
                            "confidence": 0.76,
                        }
                    ]
                },
                "allocation": {
                    "items": [
                        {
                            "symbol": "BABA",
                            "amount": 600.0,
                            "share": 0.30,
                        }
                    ]
                },
            },
        },
    }


def prepare_history(
    tmp_path: Path,
) -> Path:
    history_root = tmp_path / "history"
    package_path = history_root / RELATIVE_PATH
    package_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    package_bytes = (
        json.dumps(
            package_payload(),
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )
    package_path.write_bytes(
        package_bytes
    )

    snapshot = HistoricalSnapshot(
        snapshot_id=SNAPSHOT_ID,
        package_id="review-001",
        package_schema_version="1.0",
        product_version="0.12.0",
        generated_at=datetime(
            2026,
            8,
            3,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        archived_at=datetime(
            2026,
            8,
            3,
            17,
            36,
            tzinfo=timezone.utc,
        ),
        relative_path=RELATIVE_PATH,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
        supersedes=None,
        status="ARCHIVED",
    )
    HistoricalSnapshotManifest(
        history_root / "manifest.jsonl"
    ).append(
        snapshot
    )

    return history_root


def table_count(
    database: Path,
    table: str,
) -> int:
    import sqlite3

    with sqlite3.connect(
        database
    ) as connection:
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

    return int(
        row[0]
    )


def test_cli_imports_manifest_and_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history_root = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(history_root),
        ]
    )

    output = capsys.readouterr().out
    database = history_root / "history.db"

    assert "Historical import completed" in output
    assert "Packages imported: 1" in output
    assert database.exists()
    assert table_count(
        database,
        "snapshots",
    ) == 1
    assert table_count(
        database,
        "portfolio_summary",
    ) == 1
    assert table_count(
        database,
        "recommendations",
    ) == 1
    assert table_count(
        database,
        "deployment",
    ) == 1


def test_cli_metadata_only(
    tmp_path: Path,
) -> None:
    history_root = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(history_root),
            "--metadata-only",
        ]
    )

    database = history_root / "history.db"

    assert table_count(
        database,
        "snapshots",
    ) == 1
    assert table_count(
        database,
        "portfolio_summary",
    ) == 0


def test_cli_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history_root = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(history_root),
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "manifest"
    ]["manifest_records"] == 1
    assert report[
        "snapshots_imported"
    ] == 1
    assert report[
        "imports"
    ][0]["snapshot_id"] == SNAPSHOT_ID


def test_cli_is_safe_to_repeat(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history_root = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(history_root),
        ]
    )
    capsys.readouterr()

    main(
        [
            "--history-root",
            str(history_root),
        ]
    )

    output = capsys.readouterr().out

    assert "Metadata skipped : 1" in output
    assert "Packages imported: 0" in output


def test_cli_reports_unknown_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    history_root = prepare_history(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--history-root",
                str(history_root),
                "--snapshot-id",
                (
                    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
                ),
            ]
        )

    assert exc.value.code == 2
    assert (
        "No historical snapshot found"
        in capsys.readouterr().err
    )

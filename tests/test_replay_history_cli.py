"""
Tests for the historical replay CLI.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.replay_history import (
    main,
)
from investment_terminal.history.historical_import_state_repository import (
    HistoricalImportStateRepository,
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


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
GENERATED_AT = datetime(
    2026,
    8,
    3,
    17,
    35,
    tzinfo=timezone.utc,
)
ARCHIVED_AT = datetime(
    2026,
    8,
    3,
    17,
    36,
    tzinfo=timezone.utc,
)
STATE_AT = datetime(
    2026,
    8,
    8,
    12,
    0,
    tzinfo=timezone.utc,
)


def prepare_history(
    tmp_path: Path,
    *,
    database_path: Path | None = None,
) -> tuple[
    Path,
    Path,
    HistoricalSnapshot,
]:
    root = tmp_path / "history"
    relative_path = "2026/08/review.json"
    package_path = root / relative_path
    package_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "schema_version": "1.0",
        "generated_at": GENERATED_AT.isoformat(),
        "sections": {
            "portfolio": {
                "status": "COST_BASIS_ONLY",
            }
        },
    }
    package_bytes = (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
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
        product_version="0.13.0",
        generated_at=GENERATED_AT,
        archived_at=ARCHIVED_AT,
        relative_path=relative_path,
        checksum_sha256=hashlib.sha256(
            package_bytes
        ).hexdigest(),
        status="ARCHIVED",
    )

    database = (
        database_path
        if database_path is not None
        else root / "history.db"
    )
    store = HistoricalSQLiteStore(
        database
    )
    HistoricalSnapshotRepository(
        store
    ).add(
        snapshot
    )

    HistoricalSchemaMigrator(
        store=store,
        migrations=HISTORICAL_SCHEMA_MIGRATIONS,
        target_version=HISTORICAL_SCHEMA_TARGET_VERSION,
    ).migrate()

    HistoricalImportStateRepository(
        store
    ).initialize_metadata(
        snapshot,
        at=STATE_AT,
    )

    return (
        root,
        database,
        snapshot,
    )


def test_exact_json_returns_verified_archive(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, snapshot = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(
                root
            ),
            "--snapshot-id",
            SNAPSHOT_ID,
            "--mode",
            "exact",
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "mode"
    ] == "EXACT_ARCHIVED_PACKAGE"
    assert report[
        "exact_archived_evidence"
    ] is True
    assert report[
        "evidence_checksum_sha256"
    ] == snapshot.checksum_sha256
    assert report[
        "payload"
    ][
        "schema_version"
    ] == "1.0"


def test_normalized_json_returns_projection_with_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, _ = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(
                root
            ),
            "--snapshot-id",
            SNAPSHOT_ID,
            "--mode",
            "normalized",
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "mode"
    ] == "NORMALIZED_HISTORICAL_VIEW"
    assert report[
        "exact_archived_evidence"
    ] is False
    assert report[
        "payload"
    ][
        "import_state"
    ][
        "status"
    ] == "METADATA_ONLY"
    assert any(
        "rebuildable SQLite projection"
        in warning
        for warning in report[
            "warnings"
        ]
    )


def test_exact_human_output_identifies_verified_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, _ = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(
                root
            ),
            "--snapshot-id",
            SNAPSHOT_ID,
            "--mode",
            "exact",
        ]
    )

    output = capsys.readouterr().out

    assert "Historical replay" in output
    assert "EXACT_ARCHIVED_PACKAGE" in output
    assert "verified archived Review Package" in output


def test_normalized_human_output_exposes_state_and_counts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, _ = prepare_history(
        tmp_path
    )

    main(
        [
            "--history-root",
            str(
                root
            ),
            "--snapshot-id",
            SNAPSHOT_ID,
            "--mode",
            "normalized",
        ]
    )

    output = capsys.readouterr().out

    assert "NORMALIZED_HISTORICAL_VIEW" in output
    assert "Import state: METADATA_ONLY" in output
    assert "Holdings: 0" in output
    assert "Timeline events: 0" in output
    assert "Warnings:" in output


def test_exact_replay_reports_archive_checksum_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, snapshot = prepare_history(
        tmp_path
    )

    (
        root
        / snapshot.relative_path
    ).write_text(
        '{"changed":true}',
        encoding="utf-8",
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--history-root",
                str(
                    root
                ),
                "--snapshot-id",
                SNAPSHOT_ID,
                "--mode",
                "exact",
            ]
        )

    assert exc.value.code == 2
    assert (
        "checksum does not match"
        in capsys.readouterr().err
    )


def test_missing_database_is_actionable_and_not_created(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "history"
    database = root / "history.db"

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--history-root",
                str(
                    root
                ),
                "--snapshot-id",
                SNAPSHOT_ID,
                "--mode",
                "normalized",
            ]
        )

    assert exc.value.code == 2
    assert (
        "History database does not exist"
        in capsys.readouterr().err
    )
    assert not database.exists()


def test_custom_database_is_supported(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    custom_database = tmp_path / "custom.db"
    root, database, _ = prepare_history(
        tmp_path,
        database_path=custom_database,
    )

    assert database == custom_database

    main(
        [
            "--history-root",
            str(
                root
            ),
            "--database",
            str(
                custom_database
            ),
            "--snapshot-id",
            SNAPSHOT_ID,
            "--mode",
            "normalized",
            "--json",
        ]
    )

    report = json.loads(
        capsys.readouterr().out
    )

    assert report[
        "snapshot_id"
    ] == SNAPSHOT_ID


def test_cli_does_not_offer_current_code_recalculation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, _ = prepare_history(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--history-root",
                str(
                    root
                ),
                "--snapshot-id",
                SNAPSHOT_ID,
                "--mode",
                "current-code",
            ]
        )

    assert exc.value.code == 2
    assert (
        "invalid choice"
        in capsys.readouterr().err
    )


def test_unknown_snapshot_is_actionable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _, _ = prepare_history(
        tmp_path
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--history-root",
                str(
                    root
                ),
                "--snapshot-id",
                (
                    "7a5dc1c4-9d9a-4c17-a63c-1f8bb35e2199"
                ),
                "--mode",
                "exact",
            ]
        )

    assert exc.value.code == 2
    assert (
        "No historical snapshot found"
        in capsys.readouterr().err
    )

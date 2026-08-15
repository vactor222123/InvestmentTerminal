import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.generation_sqlite_repository import (
    SQLiteGroundedGenerationRepository,
)
from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.cli.grounded_generations import main


def at(minute: int) -> datetime:
    return datetime(
        2026,
        8,
        15,
        12,
        minute,
        tzinfo=timezone.utc,
    )


def record(
    request_id: str,
    *,
    minute: int,
) -> PersistedGroundedGeneration:
    return PersistedGroundedGeneration(
        request_id=request_id,
        generated_at=at(minute),
        prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        provider_identity="STATIC_TEST",
        model_identity="STATIC_MODEL@1",
        selected_knowledge_identities=("WORLD_A@1",),
        cited_knowledge_identities=("WORLD_A@1",),
        generation={
            "prompt": {
                "request_id": request_id,
            },
            "answer": {
                "claims": [],
            },
        },
        trace={
            "request_id": request_id,
            "validation_status": "ADMISSIBLE",
        },
    )


def database_with_records(
    tmp_path: Path,
) -> Path:
    database = tmp_path / "grounded_generations.db"
    repository = SQLiteGroundedGenerationRepository(
        GroundedGenerationSQLiteStore(
            database
        )
    )
    for item in (
        record("request-1", minute=0),
        record("request-2", minute=1),
        record("request-3", minute=2),
    ):
        repository.add(item)
    return database


def test_recent_json_uses_bounded_repository_query(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = database_with_records(
        tmp_path
    )

    main([
        "--database",
        str(database),
        "--json",
        "recent",
        "--limit",
        "2",
    ])

    report = json.loads(
        capsys.readouterr().out
    )
    assert report["command"] == "recent"
    assert report["count"] == 2
    assert [
        item["request_id"]
        for item in report["records"]
    ] == [
        "request-3",
        "request-2",
    ]


def test_between_json_uses_half_open_window(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = database_with_records(
        tmp_path
    )

    main([
        "--database",
        str(database),
        "--json",
        "between",
        "--started-at",
        at(1).isoformat(),
        "--ended-at",
        at(2).isoformat(),
    ])

    report = json.loads(
        capsys.readouterr().out
    )
    assert [
        item["request_id"]
        for item in report["records"]
    ] == [
        "request-2",
    ]


def test_show_json_returns_complete_persisted_record(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = database_with_records(
        tmp_path
    )

    main([
        "--database",
        str(database),
        "--json",
        "show",
        "--request-id",
        "request-2",
    ])

    report = json.loads(
        capsys.readouterr().out
    )
    assert report["command"] == "show"
    assert report["record"]["request_id"] == "request-2"
    assert report["record"]["trace"]["validation_status"] == (
        "ADMISSIBLE"
    )
    assert report["record"]["generation"]["prompt"][
        "request_id"
    ] == "request-2"


def test_human_output_is_compact_and_exposes_evidence_counts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = database_with_records(
        tmp_path
    )

    main([
        "--database",
        str(database),
        "show",
        "--request-id",
        "request-1",
    ])

    output = capsys.readouterr().out
    assert "Grounded Generations" in output
    assert "request-1" in output
    assert "validation=ADMISSIBLE" in output
    assert "selected=1 cited=1" in output


def test_missing_database_fails_without_creating_it(
    tmp_path: Path,
) -> None:
    database = tmp_path / "missing.db"

    with pytest.raises(SystemExit):
        main([
            "--database",
            str(database),
            "list",
        ])

    assert not database.exists()


def test_invalid_recent_limit_is_reported_as_cli_error(
    tmp_path: Path,
) -> None:
    database = database_with_records(
        tmp_path
    )

    with pytest.raises(SystemExit):
        main([
            "--database",
            str(database),
            "recent",
            "--limit",
            "0",
        ])


def test_naive_between_boundary_is_rejected_by_parser(
    tmp_path: Path,
) -> None:
    database = database_with_records(
        tmp_path
    )

    with pytest.raises(SystemExit):
        main([
            "--database",
            str(database),
            "between",
            "--started-at",
            "2026-08-15T12:00:00",
            "--ended-at",
            at(2).isoformat(),
        ])

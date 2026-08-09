from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.knowledge import (
    _build_report,
    _print_human,
    build_argument_parser,
)
from investment_terminal.knowledge.comparison import (
    KnowledgeTemporalComparisonService,
)
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)
from investment_terminal.knowledge.query_service import (
    KnowledgeQueryService,
)
from investment_terminal.knowledge.sqlite_repository import (
    SQLiteKnowledgeRecordRepository,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def record(
    *,
    version: int,
    statement: str,
    generated_at,
    valid_from=None,
    valid_to=None,
) -> KnowledgeRecord:
    vf = dt(1) if valid_from is None else valid_from
    return KnowledgeRecord(
        knowledge_id="WORLD_CONTEXT",
        knowledge_type="FACT",
        version=version,
        subject_key="WORLD",
        statement=statement,
        valid_from=vf,
        valid_to=valid_to,
        generated_at=generated_at,
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id=(
                    "11111111-1111-4111-8111-"
                    f"{version:012d}"
                ),
                observed_at=vf,
                checksum_sha256="a" * 64,
            ),
        ),
    )


def services(
    tmp_path: Path,
):
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            tmp_path / "knowledge.db"
        )
    )
    first = record(
        version=1,
        statement="First.",
        generated_at=dt(2),
        valid_to=dt(3),
    )
    second = record(
        version=2,
        statement="Second.",
        generated_at=dt(4),
        valid_from=dt(3),
    )
    repo.add(first)
    repo.add(second)
    return (
        KnowledgeQueryService(
            repository=repo
        ),
        KnowledgeTemporalComparisonService(),
    )


def test_parser_accepts_valid_command() -> None:
    options = build_argument_parser().parse_args(
        [
            "valid",
            "--subject",
            "WORLD",
            "--at",
            "2026-08-03T12:00:00+00:00",
        ]
    )

    assert options.command == "valid"
    assert options.subject == "WORLD"
    assert options.at == dt(3)


def test_list_report_contains_envelopes(
    tmp_path: Path,
) -> None:
    query, comparison = services(
        tmp_path
    )
    parser = build_argument_parser()
    options = parser.parse_args(
        ["list"]
    )

    report = _build_report(
        options,
        query=query,
        comparison=comparison,
    )

    assert report["command"] == "list"
    assert report["count"] == 2
    assert report["records"][0]["identity_key"] == "WORLD_CONTEXT@1"
    assert report["records"][0]["provenance"]["status"] == "COMPLETE"


def test_show_report_uses_exact_version(
    tmp_path: Path,
) -> None:
    query, comparison = services(
        tmp_path
    )
    options = build_argument_parser().parse_args(
        [
            "show",
            "--knowledge-id",
            "WORLD_CONTEXT",
            "--version",
            "2",
        ]
    )

    report = _build_report(
        options,
        query=query,
        comparison=comparison,
    )

    assert report["record"]["identity_key"] == "WORLD_CONTEXT@2"


def test_valid_report_uses_inclusive_validity(
    tmp_path: Path,
) -> None:
    query, comparison = services(
        tmp_path
    )
    options = build_argument_parser().parse_args(
        [
            "valid",
            "--subject",
            "WORLD",
            "--at",
            "2026-08-03T12:00:00+00:00",
        ]
    )

    report = _build_report(
        options,
        query=query,
        comparison=comparison,
    )

    assert report["count"] == 2


def test_latest_report_returns_latest_envelope(
    tmp_path: Path,
) -> None:
    query, comparison = services(
        tmp_path
    )
    options = build_argument_parser().parse_args(
        [
            "latest",
            "--subject",
            "WORLD",
        ]
    )

    report = _build_report(
        options,
        query=query,
        comparison=comparison,
    )

    assert report["record"]["identity_key"] == "WORLD_CONTEXT@2"


def test_compare_report_uses_domain_comparison(
    tmp_path: Path,
) -> None:
    query, comparison = services(
        tmp_path
    )
    options = build_argument_parser().parse_args(
        [
            "compare",
            "--knowledge-id",
            "WORLD_CONTEXT",
            "--first-version",
            "1",
            "--second-version",
            "2",
        ]
    )

    report = _build_report(
        options,
        query=query,
        comparison=comparison,
    )

    assert report["comparison"]["earlier_identity"] == "WORLD_CONTEXT@1"
    assert report["comparison"]["later_identity"] == "WORLD_CONTEXT@2"
    assert report["comparison"]["statement_changed"] is True


def test_human_output_exposes_provenance(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query, comparison = services(
        tmp_path
    )
    report = _build_report(
        build_argument_parser().parse_args(
            ["list"]
        ),
        query=query,
        comparison=comparison,
    )

    _print_human(
        "list",
        report,
    )
    output = capsys.readouterr().out

    assert "Knowledge" in output
    assert "WORLD_CONTEXT@1" in output
    assert "provenance=COMPLETE" in output


def test_compare_human_output_is_descriptive_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query, comparison = services(
        tmp_path
    )
    report = _build_report(
        build_argument_parser().parse_args(
            [
                "compare",
                "--knowledge-id",
                "WORLD_CONTEXT",
                "--first-version",
                "1",
                "--second-version",
                "2",
            ]
        ),
        query=query,
        comparison=comparison,
    )

    _print_human(
        "compare",
        report,
    )
    output = capsys.readouterr().out

    assert "Changed      : True" in output
    assert "score" not in output.lower()
    assert "confidence" not in output.lower()
    assert "effectiveness" not in output.lower()


def test_naive_valid_datetime_is_rejected() -> None:
    with pytest.raises(
        SystemExit,
    ):
        build_argument_parser().parse_args(
            [
                "valid",
                "--subject",
                "WORLD",
                "--at",
                "2026-08-03T12:00:00",
            ]
        )

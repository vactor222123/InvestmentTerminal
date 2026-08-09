import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.grounded_ai import (
    _print_human,
    _run,
    build_argument_parser,
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


def query_service(
    tmp_path: Path,
) -> KnowledgeQueryService:
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            tmp_path / "knowledge.db"
        )
    )
    repo.add(
        KnowledgeRecord(
            knowledge_id="WORLD_CONTEXT",
            knowledge_type="FACT",
            version=1,
            subject_key="WORLD",
            statement="WORLD was present historically.",
            valid_from=dt(1),
            valid_to=None,
            generated_at=dt(2),
            evidence=(
                KnowledgeEvidenceReference(
                    evidence_type="HISTORICAL_SNAPSHOT",
                    evidence_id=(
                        "11111111-1111-4111-8111-111111111111"
                    ),
                    observed_at=dt(1),
                    checksum_sha256="a" * 64,
                ),
            ),
        )
    )
    return KnowledgeQueryService(
        repository=repo
    )


def response_json():
    return json.dumps(
        {
            "answer_id": "answer-1",
            "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
            "claims": [
                {
                    "text": "Historical context is available.",
                    "citations": [
                        {
                            "knowledge_identity": "WORLD_CONTEXT@1",
                            "statement": "WORLD was present historically.",
                            "provenance_status": "COMPLETE",
                        }
                    ],
                }
            ],
        }
    )


def test_parser_accepts_reference_generation_arguments() -> None:
    options = build_argument_parser().parse_args(
        [
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--response-json",
            response_json(),
            "--subject",
            "WORLD",
            "--max-items",
            "2",
        ]
    )

    assert options.request_id == "request-1"
    assert options.query == "Question"
    assert options.subject == [
        "WORLD",
    ]
    assert options.max_items == 2


def test_run_executes_static_grounded_workflow(
    tmp_path: Path,
) -> None:
    report = _run(
        query=query_service(
            tmp_path
        ),
        request_id="request-1",
        user_query="Question",
        response_json=response_json(),
        subjects=(
            "WORLD",
        ),
        max_items=1,
    )

    assert report["generation"]["validation"]["status"] == (
        "ADMISSIBLE"
    )
    assert report["trace"]["provider_identity"] == (
        "STATIC_REFERENCE"
    )
    assert report["trace"]["model_identity"] == (
        "STATIC_REFERENCE_MODEL@1"
    )
    assert report["trace"]["selected_knowledge_identities"] == [
        "WORLD_CONTEXT@1",
    ]


def test_run_fails_closed_for_missing_citation(
    tmp_path: Path,
) -> None:
    data = json.loads(
        response_json()
    )
    data["claims"][0]["citations"][0][
        "knowledge_identity"
    ] = "MISSING@1"

    with pytest.raises(
        ValueError,
        match="not admissible",
    ):
        _run(
            query=query_service(
                tmp_path
            ),
            request_id="request-1",
            user_query="Question",
            response_json=json.dumps(
                data
            ),
            subjects=(),
            max_items=None,
        )


def test_subject_filter_can_exclude_all_context(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="not admissible",
    ):
        _run(
            query=query_service(
                tmp_path
            ),
            request_id="request-1",
            user_query="Question",
            response_json=response_json(),
            subjects=(
                "EM",
            ),
            max_items=None,
        )


def test_human_output_exposes_grounding_trace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _run(
        query=query_service(
            tmp_path
        ),
        request_id="request-1",
        user_query="Question",
        response_json=response_json(),
        subjects=(),
        max_items=None,
    )

    _print_human(
        report
    )
    output = capsys.readouterr().out

    assert "Evidence-Grounded AI" in output
    assert "Validation   : ADMISSIBLE" in output
    assert "WORLD_CONTEXT@1" in output
    assert "provenance=COMPLETE" in output


def test_reference_cli_report_contains_no_network_configuration(
    tmp_path: Path,
) -> None:
    report = _run(
        query=query_service(
            tmp_path
        ),
        request_id="request-1",
        user_query="Question",
        response_json=response_json(),
        subjects=(),
        max_items=None,
    )

    serialized = str(
        report
    ).lower()

    for key in (
        "api_key",
        "endpoint",
        "base_url",
        "temperature",
        "top_p",
    ):
        assert key not in serialized


def test_invalid_max_items_is_rejected() -> None:
    with pytest.raises(
        SystemExit,
    ):
        build_argument_parser().parse_args(
            [
                "--request-id",
                "request-1",
                "--query",
                "Question",
                "--response-json",
                response_json(),
                "--max-items",
                "0",
            ]
        )

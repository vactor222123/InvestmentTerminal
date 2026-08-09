import json
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.cli.grounded_ai import main
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
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


def seed(database: Path) -> None:
    repo = SQLiteKnowledgeRecordRepository(
        KnowledgeSQLiteStore(
            database
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


def response_json() -> str:
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


def test_real_sqlite_to_grounded_ai_json_cli_e2e(
    tmp_path: Path,
    capsys,
) -> None:
    database = tmp_path / "knowledge.db"
    seed(
        database
    )

    main(
        [
            "--database",
            str(database),
            "--json",
            "--request-id",
            "request-1",
            "--query",
            "What historical context is available?",
            "--response-json",
            response_json(),
            "--subject",
            "WORLD",
            "--max-items",
            "1",
        ]
    )

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload["generation"]["validation"]["status"] == (
        "ADMISSIBLE"
    )
    assert payload["generation"]["prompt"]["protocol_identity"] == (
        "EVIDENCE_GROUNDED_PROMPT@1"
    )
    assert payload["generation"]["answer"]["protocol_identity"] == (
        "EVIDENCE_GROUNDED_ANSWER@1"
    )
    assert payload["trace"]["request_id"] == "request-1"
    assert payload["trace"]["selected_knowledge_identities"] == [
        "WORLD_CONTEXT@1"
    ]
    assert payload["trace"]["cited_knowledge_identities"] == [
        "WORLD_CONTEXT@1"
    ]
    assert payload["trace"]["validation_status"] == "ADMISSIBLE"


def test_real_sqlite_to_grounded_ai_human_cli_e2e(
    tmp_path: Path,
    capsys,
) -> None:
    database = tmp_path / "knowledge.db"
    seed(
        database
    )

    main(
        [
            "--database",
            str(database),
            "--request-id",
            "request-1",
            "--query",
            "What historical context is available?",
            "--response-json",
            response_json(),
        ]
    )

    output = capsys.readouterr().out

    assert "Evidence-Grounded AI" in output
    assert "Validation   : ADMISSIBLE" in output
    assert "WORLD_CONTEXT@1" in output
    assert "provenance=COMPLETE" in output


def test_reference_e2e_creates_no_history_or_ai_persistence(
    tmp_path: Path,
    capsys,
) -> None:
    database = tmp_path / "knowledge.db"
    seed(
        database
    )

    main(
        [
            "--database",
            str(database),
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--response-json",
            response_json(),
        ]
    )
    capsys.readouterr()

    assert database.exists()
    assert not (
        tmp_path / "history.db"
    ).exists()
    assert not (
        tmp_path / "ai.db"
    ).exists()


def test_reference_e2e_report_contains_no_network_configuration(
    tmp_path: Path,
    capsys,
) -> None:
    database = tmp_path / "knowledge.db"
    seed(
        database
    )

    main(
        [
            "--database",
            str(database),
            "--json",
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--response-json",
            response_json(),
        ]
    )

    serialized = capsys.readouterr().out.lower()

    for key in (
        "api_key",
        "base_url",
        "endpoint",
        "temperature",
        "top_p",
        "max_tokens",
    ):
        assert key not in serialized

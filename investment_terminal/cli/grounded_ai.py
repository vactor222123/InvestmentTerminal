"""
Read-only CLI for the Evidence-Grounded AI reference workflow.

This command uses the deterministic StaticGroundedModelAdapter only. It performs
no network I/O and does not provide a real LLM/provider integration.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from investment_terminal.ai.audit import (
    GroundedGenerationTraceService,
)
from investment_terminal.ai.context_selection import (
    GroundedContextSelectionPolicy,
)
from investment_terminal.ai.model_adapter import (
    StaticGroundedModelAdapter,
)
from investment_terminal.ai.orchestration import (
    GroundedGenerationService,
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


DEFAULT_DATABASE = (
    Path("data")
    / "knowledge"
    / "knowledge.db"
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only Evidence-Grounded AI reference workflow "
            "using static model output."
        )
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Knowledge SQLite database. Default: %(default)s.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print complete JSON output.",
    )
    parser.add_argument(
        "--request-id",
        required=True,
        help="Stable correlation identifier for this generation request.",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="User query included in the grounded prompt input.",
    )
    parser.add_argument(
        "--response-json",
        required=True,
        help=(
            "Static model response JSON matching EVIDENCE_GROUNDED_ANSWER@1."
        ),
    )
    parser.add_argument(
        "--subject",
        action="append",
        default=[],
        help=(
            "Optional subject allowlist. Repeat for multiple subjects."
        ),
    )
    parser.add_argument(
        "--max-items",
        type=_positive_int,
        default=None,
        help="Optional deterministic context size cap.",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(
        argv
    )

    if not options.database.is_file():
        parser.error(
            f"Knowledge database does not exist: {options.database}"
        )

    query = KnowledgeQueryService(
        repository=SQLiteKnowledgeRecordRepository(
            KnowledgeSQLiteStore(
                options.database
            )
        )
    )

    try:
        report = _run(
            query=query,
            request_id=options.request_id,
            user_query=options.query,
            response_json=options.response_json,
            subjects=tuple(
                options.subject
            ),
            max_items=options.max_items,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.error(
            str(exc)
        )

    if options.json:
        print(
            json.dumps(
                report,
                indent=2,
                allow_nan=False,
            )
        )
        return

    _print_human(
        report
    )


def _run(
    *,
    query: KnowledgeQueryService,
    request_id: str,
    user_query: str,
    response_json: str,
    subjects: tuple[str, ...],
    max_items: int | None,
) -> dict[str, Any]:
    knowledge = query.list_all()

    policy = GroundedContextSelectionPolicy(
        subject_keys=subjects,
        max_items=max_items,
    )

    generation = GroundedGenerationService(
        adapter=StaticGroundedModelAdapter(
            provider_identity="STATIC_REFERENCE",
            model_identity="STATIC_REFERENCE_MODEL@1",
            raw_text=response_json,
        )
    ).generate(
        request_id=request_id,
        user_query=user_query,
        knowledge=knowledge,
        policy=policy,
    )

    trace = GroundedGenerationTraceService().build(
        generation
    )

    return {
        "generation": generation.to_dict(),
        "trace": trace.to_dict(),
    }


def _print_human(
    report: dict[str, Any],
) -> None:
    generation = report[
        "generation"
    ]
    trace = report[
        "trace"
    ]
    answer = generation[
        "answer"
    ]

    print("Evidence-Grounded AI")
    print(
        f"Request      : {trace['request_id']}"
    )
    print(
        "Provider     : "
        f"{trace['provider_identity']}"
    )
    print(
        "Model        : "
        f"{trace['model_identity']}"
    )
    print(
        "Validation   : "
        f"{trace['validation_status']}"
    )
    print(
        "Context      : "
        f"{len(trace['selected_knowledge_identities'])}"
    )
    print(
        f"Claims       : {trace['claim_count']}"
    )
    print(
        f"Citations    : {trace['citation_count']}"
    )

    for index, claim in enumerate(
        answer["claims"],
        start=1,
    ):
        print(
            f"  Claim {index}: {claim['text']}"
        )
        for citation in claim[
            "citations"
        ]:
            print(
                "    citation="
                f"{citation['knowledge_identity']} "
                f"provenance={citation['provenance_status']}"
            )


def _positive_int(
    value: str,
) -> int:
    try:
        parsed = int(
            value
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        ) from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


if __name__ == "__main__":
    main()

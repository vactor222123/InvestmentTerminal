"""
Live-ready read-only CLI for Evidence-Grounded AI through OpenAI.

A real network call is allowed only when --live is explicitly supplied.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from investment_terminal.ai.audit import GroundedGenerationTraceService
from investment_terminal.ai.context_selection import GroundedContextSelectionPolicy
from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
    build_openai_grounded_generation_service,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)
from investment_terminal.knowledge.query_service import KnowledgeQueryService
from investment_terminal.knowledge.sqlite_repository import SQLiteKnowledgeRecordRepository
from investment_terminal.knowledge.sqlite_store import KnowledgeSQLiteStore


DEFAULT_DATABASE = Path("data") / "knowledge" / "knowledge.db"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the read-only grounded AI workflow through the live OpenAI "
            "provider path."
        )
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--allow-model",
        action="append",
        default=[],
        help=(
            "Explicit OpenAI model identity allowed for this invocation. "
            "Repeat to allow multiple models. The requested --model must appear."
        ),
    )
    parser.add_argument("--api-key-env", default=DEFAULT_OPENAI_API_KEY_ENV)
    parser.add_argument("--timeout-seconds", type=_positive_float, default=30.0)
    parser.add_argument("--max-retries", type=_non_negative_int, default=2)
    parser.add_argument("--subject", action="append", default=[])
    parser.add_argument("--max-items", type=_positive_int, default=None)
    return parser


def _governance_policy(
    allowed_models: tuple[str, ...],
) -> GroundedProviderGovernancePolicy:
    return GroundedProviderGovernancePolicy(
        allowed_models=tuple(
            GroundedProviderModelAllowance(
                provider_identity="OPENAI",
                model_identity=model,
            )
            for model in allowed_models
        )
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(argv)

    if not options.live:
        parser.error("live OpenAI execution requires explicit --live")

    if not options.database.is_file():
        parser.error(f"Knowledge database does not exist: {options.database}")

    query = KnowledgeQueryService(
        repository=SQLiteKnowledgeRecordRepository(
            KnowledgeSQLiteStore(options.database)
        )
    )

    try:
        report = _run_live(
            query=query,
            request_id=options.request_id,
            user_query=options.query,
            model_identity=options.model,
            api_key_environment_variable=options.api_key_env,
            timeout_seconds=options.timeout_seconds,
            max_retries=options.max_retries,
            subjects=tuple(options.subject),
            max_items=options.max_items,
            governance_policy=_governance_policy(tuple(options.allow_model)),
        )
    except (KeyError, TypeError, ValueError, RuntimeError, PermissionError) as exc:
        parser.error(str(exc))

    if options.json:
        print(json.dumps(report, indent=2, allow_nan=False))
        return
    _print_human(report)


def _run_live(
    *,
    query: KnowledgeQueryService,
    request_id: str,
    user_query: str,
    model_identity: str,
    api_key_environment_variable: str,
    timeout_seconds: float,
    max_retries: int,
    subjects: tuple[str, ...],
    max_items: int | None,
    governance_policy: GroundedProviderGovernancePolicy | None = None,
    generation_service=None,
) -> dict[str, Any]:
    if generation_service is None:
        if governance_policy is None:
            raise PermissionError(
                "live provider composition requires an explicit governance policy"
            )
        service = build_openai_grounded_generation_service(
            model_identity=model_identity,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            governance_policy=governance_policy,
            api_key_environment_variable=api_key_environment_variable,
        )
    else:
        service = generation_service

    knowledge = query.list_all()
    generation = service.generate(
        request_id=request_id,
        user_query=user_query,
        knowledge=knowledge,
        policy=GroundedContextSelectionPolicy(
            subject_keys=subjects,
            max_items=max_items,
        ),
    )
    trace = GroundedGenerationTraceService().build(generation)
    return {"generation": generation.to_dict(), "trace": trace.to_dict()}


def _print_human(report: dict[str, Any]) -> None:
    trace = report["trace"]
    answer = report["generation"]["answer"]
    print("Evidence-Grounded AI — Live OpenAI")
    print(f"Request      : {trace['request_id']}")
    print(f"Provider     : {trace['provider_identity']}")
    print(f"Model        : {trace['model_identity']}")
    provider_operation = trace.get("provider_operation")
    if provider_operation is not None:
        print(f"Attempts     : {provider_operation['attempt_count']}")
        print(f"Retries      : {provider_operation['retry_count']}")
        print(f"HTTP Status  : {provider_operation['transport_status_code']}")
        print(f"Transport    : {provider_operation['transport_outcome']}")
    print(f"Validation   : {trace['validation_status']}")
    print(f"Context      : {len(trace['selected_knowledge_identities'])}")
    print(f"Claims       : {trace['claim_count']}")
    print(f"Citations    : {trace['citation_count']}")
    for index, claim in enumerate(answer["claims"], start=1):
        print(f"  Claim {index}: {claim['text']}")
        for citation in claim["citations"]:
            print(
                "    citation="
                f"{citation['knowledge_identity']} "
                f"provenance={citation['provenance_status']}"
            )


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return parsed


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive number")
    return parsed


if __name__ == "__main__":
    main()

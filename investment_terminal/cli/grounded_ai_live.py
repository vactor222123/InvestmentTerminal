"""
Live-ready read-only CLI for Evidence-Grounded AI through OpenAI.

A real network call is allowed only when --live is explicitly supplied.
Pricing, budget, and retry-delay controls are explicit per invocation.

The CLI is a thin adapter over the grounded AI application service.
"""

import argparse
import json
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from investment_terminal.ai.providers.composition import (
    DEFAULT_OPENAI_API_KEY_ENV,
    build_openai_grounded_generation_service,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)
from investment_terminal.ai.providers.guardrails import (
    GroundedProviderBudgetPolicy,
)
from investment_terminal.ai.providers.pricing import (
    GroundedProviderPricingEntry,
    GroundedProviderPricingPolicy,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
)
from investment_terminal.application.live_grounded_ai import (
    LiveGroundedAIApplicationService,
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

DEFAULT_DATABASE = Path("data") / "knowledge" / "knowledge.db"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--allow-model", action="append", default=[])
    parser.add_argument("--api-key-env", default=DEFAULT_OPENAI_API_KEY_ENV)
    parser.add_argument("--timeout-seconds", type=_positive_float, default=30.0)
    parser.add_argument("--max-retries", type=_non_negative_int, default=2)

    parser.add_argument(
        "--retry-initial-delay-seconds",
        type=_non_negative_decimal,
    )
    parser.add_argument(
        "--retry-delay-multiplier",
        type=_decimal_at_least_one,
    )
    parser.add_argument(
        "--retry-maximum-delay-seconds",
        type=_non_negative_decimal,
    )

    parser.add_argument("--subject", action="append", default=[])
    parser.add_argument("--max-items", type=_positive_int, default=None)

    parser.add_argument("--max-output-tokens", type=_positive_int)
    parser.add_argument("--max-total-tokens", type=_positive_int)
    parser.add_argument("--max-total-cost", type=_non_negative_decimal)
    parser.add_argument("--budget-currency")

    parser.add_argument("--pricing-currency")
    parser.add_argument("--input-cost-per-million", type=_non_negative_decimal)
    parser.add_argument("--output-cost-per-million", type=_non_negative_decimal)
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


def _pricing_policy(
    *,
    model_identity: str,
    currency: str | None,
    input_cost_per_million: Decimal | None,
    output_cost_per_million: Decimal | None,
) -> GroundedProviderPricingPolicy | None:
    supplied = (
        currency is not None,
        input_cost_per_million is not None,
        output_cost_per_million is not None,
    )
    if not any(supplied):
        return None
    if not all(supplied):
        raise ValueError(
            "pricing requires --pricing-currency, "
            "--input-cost-per-million, and --output-cost-per-million together"
        )

    assert currency is not None
    assert input_cost_per_million is not None
    assert output_cost_per_million is not None

    return GroundedProviderPricingPolicy(
        entries=(
            GroundedProviderPricingEntry(
                provider_identity="OPENAI",
                model_identity=model_identity,
                currency=currency,
                input_cost_per_million_tokens=input_cost_per_million,
                output_cost_per_million_tokens=output_cost_per_million,
            ),
        )
    )


def _budget_policy(
    *,
    max_output_tokens: int | None,
    max_total_tokens: int | None,
    max_total_cost: Decimal | None,
    currency: str | None,
) -> GroundedProviderBudgetPolicy | None:
    supplied = (
        max_output_tokens is not None,
        max_total_tokens is not None,
        max_total_cost is not None,
        currency is not None,
    )
    if not any(supplied):
        return None
    return GroundedProviderBudgetPolicy(
        max_output_tokens=max_output_tokens,
        max_total_tokens=max_total_tokens,
        max_total_cost=max_total_cost,
        currency=currency,
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
        pricing_policy = _pricing_policy(
            model_identity=options.model,
            currency=options.pricing_currency,
            input_cost_per_million=options.input_cost_per_million,
            output_cost_per_million=options.output_cost_per_million,
        )
        budget_policy = _budget_policy(
            max_output_tokens=options.max_output_tokens,
            max_total_tokens=options.max_total_tokens,
            max_total_cost=options.max_total_cost,
            currency=options.budget_currency,
        )

        if (
            budget_policy is not None
            and budget_policy.max_total_cost is not None
            and pricing_policy is None
        ):
            raise ValueError(
                "max total cost budget requires explicit pricing configuration"
            )

        report = _run_live(
            query=query,
            request_id=options.request_id,
            user_query=options.query,
            model_identity=options.model,
            api_key_environment_variable=options.api_key_env,
            timeout_seconds=options.timeout_seconds,
            max_retries=options.max_retries,
            retry_initial_delay_seconds=options.retry_initial_delay_seconds,
            retry_delay_multiplier=options.retry_delay_multiplier,
            retry_maximum_delay_seconds=options.retry_maximum_delay_seconds,
            subjects=tuple(options.subject),
            max_items=options.max_items,
            governance_policy=_governance_policy(tuple(options.allow_model)),
            pricing_policy=pricing_policy,
            budget_policy=budget_policy,
            requested_max_output_tokens=options.max_output_tokens,
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        PermissionError,
        LookupError,
    ) as exc:
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
    retry_initial_delay_seconds: Decimal | None = None,
    retry_delay_multiplier: Decimal | None = None,
    retry_maximum_delay_seconds: Decimal | None = None,
    subjects: tuple[str, ...],
    max_items: int | None,
    governance_policy: GroundedProviderGovernancePolicy | None = None,
    pricing_policy: GroundedProviderPricingPolicy | None = None,
    budget_policy: GroundedProviderBudgetPolicy | None = None,
    requested_max_output_tokens: int | None = None,
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
            max_output_tokens=requested_max_output_tokens,
            retry_initial_delay_seconds=retry_initial_delay_seconds,
            retry_delay_multiplier=retry_delay_multiplier,
            retry_maximum_delay_seconds=retry_maximum_delay_seconds,
            api_key_environment_variable=api_key_environment_variable,
        )
    else:
        service = generation_service

    application = LiveGroundedAIApplicationService(
        query=query,
        generation_service=service,
        pricing_policy=pricing_policy,
        budget_policy=budget_policy,
        requested_max_output_tokens=requested_max_output_tokens,
    )

    result = application.execute(
        GroundedAIApplicationRequest(
            request_id=request_id,
            user_query=user_query,
            subject_keys=subjects,
            max_items=max_items,
        )
    )
    return result.to_dict()


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
        retry_delays = provider_operation.get(
            "retry_delay_seconds"
        )
        if retry_delays:
            print(
                "Retry Delays : "
                + ", ".join(retry_delays)
                + " s"
            )
        print(f"HTTP Status  : {provider_operation['transport_status_code']}")
        print(f"Transport    : {provider_operation['transport_outcome']}")

    provider_usage = trace.get("provider_usage")
    if provider_usage is not None:
        print(f"Input Tokens : {provider_usage['input_tokens']:,}")
        print(f"Output Tokens: {provider_usage['output_tokens']:,}")
        print(f"Total Tokens : {provider_usage['total_tokens']:,}")

    provider_cost = trace.get("provider_cost")
    if provider_cost is not None:
        print(
            "Input Cost   : "
            f"{provider_cost['input_cost']} {provider_cost['currency']}"
        )
        print(
            "Output Cost  : "
            f"{provider_cost['output_cost']} {provider_cost['currency']}"
        )
        print(
            "Total Cost   : "
            f"{provider_cost['total_cost']} {provider_cost['currency']}"
        )

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
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        ) from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be a non-negative integer"
        ) from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError(
            "value must be a non-negative integer"
        )
    return parsed


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be a positive number"
        ) from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive number"
        )
    return parsed


def _non_negative_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(
            "value must be a non-negative decimal"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise argparse.ArgumentTypeError(
            "value must be a non-negative decimal"
        )
    return parsed


def _decimal_at_least_one(value: str) -> Decimal:
    parsed = _non_negative_decimal(value)
    if parsed < Decimal("1"):
        raise argparse.ArgumentTypeError(
            "value must be at least 1"
        )
    return parsed


if __name__ == "__main__":
    main()

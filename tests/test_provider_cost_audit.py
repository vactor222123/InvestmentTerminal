from decimal import Decimal

import pytest

from investment_terminal.ai.audit import GroundedGenerationTrace
from investment_terminal.ai.providers.cost_audit import (
    GroundedProviderCostTraceService,
)
from investment_terminal.ai.providers.pricing import (
    GroundedProviderPricingEntry,
    GroundedProviderPricingPolicy,
)


def trace_with_usage():
    return GroundedGenerationTrace(
        request_id="r1",
        prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        provider_identity="OPENAI",
        model_identity="gpt-test",
        selected_knowledge_identities=("WORLD@1",),
        cited_knowledge_identities=("WORLD@1",),
        claim_count=1,
        citation_count=1,
        validation_status="ADMISSIBLE",
        provider_input_tokens=1000,
        provider_output_tokens=500,
        provider_total_tokens=1500,
    )


def pricing():
    return GroundedProviderPricingPolicy(
        entries=(
            GroundedProviderPricingEntry(
                provider_identity="OPENAI",
                model_identity="gpt-test",
                currency="USD",
                input_cost_per_million_tokens=Decimal("2.50"),
                output_cost_per_million_tokens=Decimal("10.00"),
            ),
        )
    )


def test_cost_trace_adds_provider_cost_when_usage_and_pricing_exist() -> None:
    data = GroundedProviderCostTraceService().build(
        trace=trace_with_usage(),
        pricing_policy=pricing(),
    )

    assert data["provider_cost"] == {
        "provider_identity": "OPENAI",
        "model_identity": "gpt-test",
        "currency": "USD",
        "input_cost": "0.002500",
        "output_cost": "0.005000",
        "total_cost": "0.007500",
    }


def test_trace_without_usage_remains_without_cost() -> None:
    trace = GroundedGenerationTrace(
        request_id="r1",
        prompt_protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        answer_protocol_identity="EVIDENCE_GROUNDED_ANSWER@1",
        provider_identity="STATIC",
        model_identity="STATIC@1",
        selected_knowledge_identities=("WORLD@1",),
        cited_knowledge_identities=("WORLD@1",),
        claim_count=1,
        citation_count=1,
        validation_status="ADMISSIBLE",
    )

    data = GroundedProviderCostTraceService().build(
        trace=trace,
        pricing_policy=GroundedProviderPricingPolicy(entries=()),
    )

    assert "provider_cost" not in data


def test_unknown_pricing_fails_closed_when_usage_exists() -> None:
    with pytest.raises(LookupError):
        GroundedProviderCostTraceService().build(
            trace=trace_with_usage(),
            pricing_policy=GroundedProviderPricingPolicy(entries=()),
        )


def test_cost_trace_does_not_mutate_original_trace_serialization() -> None:
    trace = trace_with_usage()
    before = trace.to_dict()

    GroundedProviderCostTraceService().build(
        trace=trace,
        pricing_policy=pricing(),
    )

    assert trace.to_dict() == before
    assert "provider_cost" not in before

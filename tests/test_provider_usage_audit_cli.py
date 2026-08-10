import json

import pytest

from investment_terminal.ai.audit import GroundedGenerationTrace
from investment_terminal.cli.grounded_ai_live import _print_human


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
        provider_input_tokens=1234,
        provider_output_tokens=156,
        provider_total_tokens=1390,
    )


def test_trace_serializes_provider_usage() -> None:
    assert trace_with_usage().to_dict()["provider_usage"] == {
        "input_tokens": 1234,
        "output_tokens": 156,
        "total_tokens": 1390,
    }


def test_trace_without_usage_is_backward_compatible() -> None:
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
    assert "provider_usage" not in trace.to_dict()


def test_human_output_exposes_token_totals(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {
        "trace": trace_with_usage().to_dict(),
        "generation": {
            "answer": {
                "claims": [
                    {
                        "text": "Claim",
                        "citations": [
                            {
                                "knowledge_identity": "WORLD@1",
                                "provenance_status": "COMPLETE",
                            }
                        ],
                    }
                ]
            }
        },
    }

    _print_human(report)
    output = capsys.readouterr().out

    assert "Input Tokens : 1,234" in output
    assert "Output Tokens: 156" in output
    assert "Total Tokens : 1,390" in output


def test_usage_output_contains_no_cost_or_secret_data() -> None:
    serialized = json.dumps(
        trace_with_usage().to_dict()["provider_usage"]
    ).lower()
    for forbidden in (
        "cost",
        "price",
        "currency",
        "api_key",
        "authorization",
        "headers",
        "body",
    ):
        assert forbidden not in serialized

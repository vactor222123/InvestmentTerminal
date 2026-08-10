import json

import pytest

from investment_terminal.cli.grounded_ai_live import (
    _print_human,
)


def report_with_provider_operation():
    return {
        "generation": {
            "answer": {
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
                ]
            }
        },
        "trace": {
            "request_id": "request-1",
            "provider_identity": "OPENAI",
            "model_identity": "gpt-test",
            "selected_knowledge_identities": [
                "WORLD_CONTEXT@1"
            ],
            "cited_knowledge_identities": [
                "WORLD_CONTEXT@1"
            ],
            "claim_count": 1,
            "citation_count": 1,
            "validation_status": "ADMISSIBLE",
            "provider_operation": {
                "attempt_count": 2,
                "retry_count": 1,
                "transport_status_code": 200,
                "transport_outcome": "SUCCESS",
            },
        },
    }


def test_live_human_output_exposes_safe_provider_operation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _print_human(
        report_with_provider_operation()
    )

    output = capsys.readouterr().out

    assert "Provider     : OPENAI" in output
    assert "Model        : gpt-test" in output
    assert "Attempts     : 2" in output
    assert "Retries      : 1" in output
    assert "HTTP Status  : 200" in output
    assert "Transport    : SUCCESS" in output
    assert "Validation   : ADMISSIBLE" in output


def test_human_output_does_not_require_provider_operation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = report_with_provider_operation()
    del report["trace"][
        "provider_operation"
    ]

    _print_human(
        report
    )

    output = capsys.readouterr().out

    assert "Provider     : OPENAI" in output
    assert "Validation   : ADMISSIBLE" in output
    assert "Attempts" not in output
    assert "Retries" not in output
    assert "HTTP Status" not in output
    assert "Transport" not in output


def test_provider_operation_json_shape_contains_no_secret_transport_data() -> None:
    operation = report_with_provider_operation()[
        "trace"
    ][
        "provider_operation"
    ]

    assert operation == {
        "attempt_count": 2,
        "retry_count": 1,
        "transport_status_code": 200,
        "transport_outcome": "SUCCESS",
    }

    serialized = json.dumps(
        operation
    ).lower()

    for forbidden in (
        "authorization",
        "api_key",
        "headers",
        "body",
        "url",
        "raw_text",
        "secret",
    ):
        assert forbidden not in serialized


def test_human_output_does_not_render_secret_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _print_human(
        report_with_provider_operation()
    )

    output = capsys.readouterr().out.lower()

    for forbidden in (
        "authorization",
        "api_key",
        "bearer ",
        "raw_text",
        "https://api.openai.com",
    ):
        assert forbidden not in output

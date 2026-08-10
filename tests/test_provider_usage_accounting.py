import json

import pytest

from investment_terminal.ai.model_adapter import (
    GroundedModelResponse,
    GroundedProviderUsage,
)
from investment_terminal.ai.providers.openai_adapter import (
    OpenAIGroundedModelAdapter,
)


def test_provider_usage_requires_consistent_total() -> None:
    usage = GroundedProviderUsage(
        input_tokens=120,
        output_tokens=30,
        total_tokens=150,
    )
    assert usage.to_dict() == {
        "input_tokens": 120,
        "output_tokens": 30,
        "total_tokens": 150,
    }

    with pytest.raises(
        ValueError,
        match="must equal",
    ):
        GroundedProviderUsage(
            input_tokens=120,
            output_tokens=30,
            total_tokens=151,
        )


def test_model_response_usage_is_optional_and_serializable() -> None:
    response = GroundedModelResponse(
        request_id="r1",
        provider_identity="OPENAI",
        model_identity="gpt-test",
        raw_text="{}",
        usage=GroundedProviderUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        ),
    )
    assert response.to_dict()["usage"] == {
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
    }


def test_static_compatibility_has_no_usage_key() -> None:
    response = GroundedModelResponse(
        request_id="r1",
        provider_identity="STATIC",
        model_identity="STATIC@1",
        raw_text="{}",
    )
    assert response.usage is None
    assert "usage" not in response.to_dict()


def test_openai_usage_extracts_provider_neutral_totals() -> None:
    payload = {
        "usage": {
            "input_tokens": 120,
            "input_tokens_details": {
                "cached_tokens": 100,
            },
            "output_tokens": 30,
            "output_tokens_details": {
                "reasoning_tokens": 20,
            },
            "total_tokens": 150,
        }
    }

    usage = OpenAIGroundedModelAdapter._extract_usage_from_payload(
        payload
    )

    assert usage == GroundedProviderUsage(
        input_tokens=120,
        output_tokens=30,
        total_tokens=150,
    )


def test_openai_usage_null_is_supported() -> None:
    assert (
        OpenAIGroundedModelAdapter._extract_usage_from_payload(
            {"usage": None}
        )
        is None
    )


@pytest.mark.parametrize(
    "usage",
    [
        {},
        {"input_tokens": 1, "output_tokens": 2},
        {
            "input_tokens": -1,
            "output_tokens": 2,
            "total_tokens": 1,
        },
        {
            "input_tokens": True,
            "output_tokens": 2,
            "total_tokens": 3,
        },
    ],
)
def test_malformed_openai_usage_fails_closed(
    usage,
) -> None:
    with pytest.raises(ValueError):
        OpenAIGroundedModelAdapter._extract_usage_from_payload(
            {"usage": usage}
        )


def test_usage_contract_contains_no_cost_or_provider_breakdown() -> None:
    data = GroundedProviderUsage(
        input_tokens=100,
        output_tokens=25,
        total_tokens=125,
    ).to_dict()
    serialized = json.dumps(data).lower()
    for forbidden in (
        "cost",
        "price",
        "currency",
        "cached_tokens",
        "reasoning_tokens",
        "provider",
        "model",
    ):
        assert forbidden not in serialized

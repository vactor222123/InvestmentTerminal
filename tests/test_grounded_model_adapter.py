from abc import ABC

import pytest

from investment_terminal.ai.model_adapter import (
    GroundedModelAdapter,
    GroundedModelResponse,
    StaticGroundedModelAdapter,
)
from investment_terminal.ai.prompt_input import (
    GroundedPromptInput,
)


def prompt() -> GroundedPromptInput:
    return GroundedPromptInput(
        request_id="request-1",
        protocol_identity="EVIDENCE_GROUNDED_PROMPT@1",
        user_query="What historical context is available?",
        context=(),
    )


def test_model_adapter_is_abstract_contract() -> None:
    assert issubclass(
        GroundedModelAdapter,
        ABC,
    )

    with pytest.raises(
        TypeError,
    ):
        GroundedModelAdapter()  # type: ignore[abstract]


def test_static_reference_adapter_preserves_request_correlation() -> None:
    adapter = StaticGroundedModelAdapter(
        provider_identity="STATIC_TEST",
        model_identity="STATIC_MODEL@1",
        raw_text="Raw grounded output.",
    )

    response = adapter.generate(
        prompt()
    )

    assert response.request_id == "request-1"
    assert response.provider_identity == "STATIC_TEST"
    assert response.model_identity == "STATIC_MODEL@1"
    assert response.raw_text == "Raw grounded output."


def test_response_serialization_is_provider_neutral() -> None:
    response = GroundedModelResponse(
        request_id="request-1",
        provider_identity="TEST_PROVIDER",
        model_identity="TEST_MODEL@1",
        raw_text="Raw output.",
    )

    assert response.to_dict() == {
        "request_id": "request-1",
        "provider_identity": "TEST_PROVIDER",
        "model_identity": "TEST_MODEL@1",
        "raw_text": "Raw output.",
    }


def test_static_adapter_rejects_wrong_prompt_type() -> None:
    adapter = StaticGroundedModelAdapter(
        provider_identity="STATIC_TEST",
        model_identity="STATIC_MODEL@1",
        raw_text="Raw grounded output.",
    )

    with pytest.raises(
        TypeError,
        match="GroundedPromptInput",
    ):
        adapter.generate(
            object()  # type: ignore[arg-type]
        )


def test_response_contains_no_parsed_claim_or_grounding_semantics() -> None:
    serialized = str(
        GroundedModelResponse(
            request_id="request-1",
            provider_identity="TEST_PROVIDER",
            model_identity="TEST_MODEL@1",
            raw_text="Raw output.",
        ).to_dict()
    ).lower()

    for key in (
        "claims",
        "citations",
        "provenance_status",
        "confidence",
        "prediction",
        "effectiveness",
    ):
        assert key not in serialized


def test_contract_imports_no_specific_provider_sdk() -> None:
    import investment_terminal.ai.model_adapter as module

    names = {
        name.lower()
        for name in module.__dict__
    }

    forbidden = (
        "openai",
        "anthropic",
        "google",
        "groq",
        "mistral",
    )
    assert not any(
        provider in names
        for provider in forbidden
    )

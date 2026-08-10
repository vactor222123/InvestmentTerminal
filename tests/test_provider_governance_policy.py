import pytest

from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)


def allowance(
    provider="OPENAI",
    model="gpt-test",
):
    return GroundedProviderModelAllowance(
        provider_identity=provider,
        model_identity=model,
    )


def test_explicit_provider_model_pair_is_allowed() -> None:
    policy = GroundedProviderGovernancePolicy(
        allowed_models=(
            allowance(),
        )
    )

    assessment = policy.assess(
        provider_identity="openai",
        model_identity="gpt-test",
    )

    assert assessment.status == "ALLOWED"
    assert assessment.allowed is True
    assert assessment.provider_identity == "OPENAI"
    assert assessment.model_identity == "gpt-test"


def test_unknown_model_is_denied_fail_closed() -> None:
    policy = GroundedProviderGovernancePolicy(
        allowed_models=(
            allowance(),
        )
    )

    assessment = policy.assess(
        provider_identity="OPENAI",
        model_identity="gpt-other",
    )

    assert assessment.status == "DENIED"
    assert assessment.allowed is False


def test_unknown_provider_is_denied_fail_closed() -> None:
    policy = GroundedProviderGovernancePolicy(
        allowed_models=(
            allowance(),
        )
    )

    with pytest.raises(
        PermissionError,
        match="not allowed by governance policy",
    ):
        policy.require_allowed(
            provider_identity="OTHER",
            model_identity="gpt-test",
        )


def test_empty_policy_denies_everything() -> None:
    policy = GroundedProviderGovernancePolicy(
        allowed_models=()
    )

    with pytest.raises(
        PermissionError,
    ):
        policy.require_allowed(
            provider_identity="OPENAI",
            model_identity="gpt-test",
        )


def test_duplicate_provider_model_pair_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        GroundedProviderGovernancePolicy(
            allowed_models=(
                allowance(),
                allowance(
                    provider="openai",
                    model="gpt-test",
                ),
            )
        )


def test_policy_serialization_contains_no_credentials_or_network_config() -> None:
    policy = GroundedProviderGovernancePolicy(
        allowed_models=(
            allowance(),
        )
    )

    data = policy.to_dict()

    assert data == {
        "allowed_models": [
            {
                "provider_identity": "OPENAI",
                "model_identity": "gpt-test",
            }
        ]
    }

    serialized = str(data).lower()
    for forbidden in (
        "api_key",
        "authorization",
        "timeout",
        "retry",
        "url",
        "endpoint",
    ):
        assert forbidden not in serialized


def test_allowed_identity_keys_are_deterministic() -> None:
    policy = GroundedProviderGovernancePolicy(
        allowed_models=(
            allowance(
                provider="OPENAI",
                model="z-model",
            ),
            allowance(
                provider="OTHER",
                model="a-model",
            ),
        )
    )

    assert policy.allowed_identity_keys == (
        "OPENAI:z-model",
        "OTHER:a-model",
    )

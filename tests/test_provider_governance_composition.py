import pytest

from investment_terminal.ai.providers.composition import (
    build_openai_grounded_generation_service,
)
from investment_terminal.ai.providers.governance import (
    GroundedProviderGovernancePolicy,
    GroundedProviderModelAllowance,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportResponse,
)


def policy(
    model="gpt-test",
):
    return GroundedProviderGovernancePolicy(
        allowed_models=(
            GroundedProviderModelAllowance(
                provider_identity="OPENAI",
                model_identity=model,
            ),
        )
    )


class RecordingTransport(
    GroundedProviderTransport
):
    def __init__(self) -> None:
        self.calls = 0

    def send(self, request):
        self.calls += 1
        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=200,
            headers=(),
            body='{"status":"completed","output":[]}',
        )


def test_allowed_model_builds_production_service() -> None:
    service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=1,
        governance_policy=policy(),
        transport=RecordingTransport(),
    )

    assert service is not None


def test_denied_model_fails_before_transport_use() -> None:
    transport = RecordingTransport()

    with pytest.raises(
        PermissionError,
        match="not allowed by governance policy",
    ):
        build_openai_grounded_generation_service(
            model_identity="gpt-denied",
            timeout_seconds=10,
            max_retries=1,
            governance_policy=policy(
                model="gpt-allowed"
            ),
            transport=transport,
        )

    assert transport.calls == 0


def test_empty_policy_denies_production_composition() -> None:
    with pytest.raises(
        PermissionError,
    ):
        build_openai_grounded_generation_service(
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=1,
            governance_policy=GroundedProviderGovernancePolicy(
                allowed_models=()
            ),
            transport=RecordingTransport(),
        )


def test_governance_policy_is_mandatory_and_typed() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedProviderGovernancePolicy",
    ):
        build_openai_grounded_generation_service(
            model_identity="gpt-test",
            timeout_seconds=10,
            max_retries=1,
            governance_policy=object(),  # type: ignore[arg-type]
            transport=RecordingTransport(),
        )


def test_denied_model_does_not_require_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        raising=False,
    )

    with pytest.raises(
        PermissionError,
    ):
        build_openai_grounded_generation_service(
            model_identity="gpt-denied",
            timeout_seconds=10,
            max_retries=1,
            governance_policy=policy(
                model="gpt-allowed"
            ),
            transport=RecordingTransport(),
        )


def test_allowed_model_still_defers_secret_lookup_until_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        raising=False,
    )

    service = build_openai_grounded_generation_service(
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=1,
        governance_policy=policy(),
        transport=RecordingTransport(),
    )

    assert service is not None

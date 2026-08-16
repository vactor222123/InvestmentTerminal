from investment_terminal.server.deployment_security import (
    APPLICATION_TRANSPORT_PRIVATE_HTTP,
    HEALTH_EXPOSURE_LIVENESS,
    OPENAPI_EXPOSURE_PRIVATE,
    READY_EXPOSURE_PRIVATE,
    SECRET_INJECTION_PROCESS_ENVIRONMENT,
    TLS_TERMINATION_REVERSE_PROXY_OR_PLATFORM,
    GroundedAIServerDeploymentSecurityContract,
)


def test_deployment_security_contract_has_explicit_ownership() -> None:
    contract = GroundedAIServerDeploymentSecurityContract()

    assert contract.tls_termination == (
        TLS_TERMINATION_REVERSE_PROXY_OR_PLATFORM
    )
    assert contract.application_transport == (
        APPLICATION_TRANSPORT_PRIVATE_HTTP
    )
    assert contract.secret_injection == (
        SECRET_INJECTION_PROCESS_ENVIRONMENT
    )


def test_deployment_security_contract_does_not_trust_forwarded_headers() -> None:
    contract = GroundedAIServerDeploymentSecurityContract()

    assert contract.trust_forwarded_headers is False
    assert contract.direct_public_application_exposure_supported is False


def test_deployment_security_contract_preserves_application_authentication() -> None:
    contract = GroundedAIServerDeploymentSecurityContract()

    assert contract.api_key_authentication_required is True


def test_deployment_security_contract_distinguishes_endpoint_exposure() -> None:
    contract = GroundedAIServerDeploymentSecurityContract()

    assert contract.health_exposure == HEALTH_EXPOSURE_LIVENESS
    assert contract.ready_exposure == READY_EXPOSURE_PRIVATE
    assert contract.openapi_exposure == OPENAPI_EXPOSURE_PRIVATE

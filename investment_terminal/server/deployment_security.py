"""Canonical deployment-security ownership contract."""

from dataclasses import dataclass
from typing import Final


TLS_TERMINATION_REVERSE_PROXY_OR_PLATFORM: Final = (
    "REVERSE_PROXY_OR_PLATFORM"
)
APPLICATION_TRANSPORT_PRIVATE_HTTP: Final = "PRIVATE_HTTP"
SECRET_INJECTION_PROCESS_ENVIRONMENT: Final = "PROCESS_ENVIRONMENT"
HEALTH_EXPOSURE_LIVENESS: Final = "LIVENESS_ENDPOINT"
READY_EXPOSURE_PRIVATE: Final = "PRIVATE_READINESS_ENDPOINT"
OPENAPI_EXPOSURE_PRIVATE: Final = "PRIVATE_OPERATOR_SCHEMA"


@dataclass(frozen=True, slots=True)
class GroundedAIServerDeploymentSecurityContract:
    """
    Describe responsibility boundaries for a production deployment.

    The object is intentionally descriptive. Network policy, TLS certificates,
    secret-manager integration, and reverse-proxy configuration remain owned by
    deployment infrastructure.
    """

    tls_termination: str = TLS_TERMINATION_REVERSE_PROXY_OR_PLATFORM
    application_transport: str = APPLICATION_TRANSPORT_PRIVATE_HTTP
    secret_injection: str = SECRET_INJECTION_PROCESS_ENVIRONMENT
    health_exposure: str = HEALTH_EXPOSURE_LIVENESS
    ready_exposure: str = READY_EXPOSURE_PRIVATE
    openapi_exposure: str = OPENAPI_EXPOSURE_PRIVATE
    trust_forwarded_headers: bool = False
    api_key_authentication_required: bool = True
    direct_public_application_exposure_supported: bool = False

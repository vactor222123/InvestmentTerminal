"""
Environment-backed provider credential source.

This module reads explicitly mapped environment variables on demand. It does
not load .env files, persist secrets, log secret values, or perform network I/O.
"""

import os
from collections.abc import Mapping

from investment_terminal.ai.providers.contracts import (
    GroundedProviderCredentialSource,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


class EnvironmentGroundedProviderCredentialSource(
    GroundedProviderCredentialSource
):
    """Resolve provider API keys from an explicit environment-variable map."""

    def __init__(
        self,
        *,
        variable_by_provider: Mapping[str, str],
    ) -> None:
        if not isinstance(
            variable_by_provider,
            Mapping,
        ):
            raise TypeError(
                "variable_by_provider must be a mapping"
            )

        normalized: dict[str, str] = {}
        for provider_identity, variable_name in variable_by_provider.items():
            provider = normalize_required_text(
                provider_identity,
                field_name="provider_identity",
            )
            variable = normalize_required_text(
                variable_name,
                field_name="variable_name",
            )

            if provider in normalized:
                raise ValueError(
                    "provider identities must be unique"
                )

            normalized[
                provider
            ] = variable

        if not normalized:
            raise ValueError(
                "variable_by_provider must not be empty"
            )

        self._variable_by_provider = normalized

    def get_api_key(
        self,
        *,
        provider_identity: str,
    ) -> str:
        provider = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
        )

        try:
            variable_name = self._variable_by_provider[
                provider
            ]
        except KeyError as exc:
            raise KeyError(
                f"No environment credential mapping for provider: {provider}"
            ) from exc

        raw_value = os.environ.get(
            variable_name
        )
        if raw_value is None:
            raise RuntimeError(
                f"Required credential environment variable is not set: "
                f"{variable_name}"
            )

        try:
            return normalize_required_text(
                raw_value,
                field_name="api_key",
            )
        except ValueError as exc:
            raise RuntimeError(
                f"Required credential environment variable is empty: "
                f"{variable_name}"
            ) from exc

    def configured_providers(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                self._variable_by_provider
            )
        )

    def environment_variable_name(
        self,
        *,
        provider_identity: str,
    ) -> str:
        provider = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
        )
        try:
            return self._variable_by_provider[
                provider
            ]
        except KeyError as exc:
            raise KeyError(
                f"No environment credential mapping for provider: {provider}"
            ) from exc

    def __repr__(self) -> str:
        providers = ", ".join(
            self.configured_providers()
        )
        return (
            "EnvironmentGroundedProviderCredentialSource("
            f"providers=({providers})"
            ")"
        )

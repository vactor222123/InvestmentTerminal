"""
Explicit provider/model governance policy for live grounded AI execution.

This module defines a fail-closed allowlist contract only. It performs no
credential lookup, model invocation, transport I/O, or persistence.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedProviderModelAllowance:
    """One explicitly permitted provider/model pair."""

    provider_identity: str
    model_identity: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_identity",
            normalize_required_text(
                self.provider_identity,
                field_name="provider_identity",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "model_identity",
            normalize_required_text(
                self.model_identity,
                field_name="model_identity",
            ),
        )

    @property
    def identity_key(self) -> str:
        return (
            f"{self.provider_identity}"
            f":{self.model_identity}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderGovernanceAssessment:
    """Deterministic allow/deny assessment for one requested provider/model."""

    provider_identity: str
    model_identity: str
    status: str
    reason: str

    ALLOWED = "ALLOWED"
    DENIED = "DENIED"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_identity",
            normalize_required_text(
                self.provider_identity,
                field_name="provider_identity",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "model_identity",
            normalize_required_text(
                self.model_identity,
                field_name="model_identity",
            ),
        )
        object.__setattr__(
            self,
            "status",
            normalize_required_text(
                self.status,
                field_name="status",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "reason",
            normalize_required_text(
                self.reason,
                field_name="reason",
            ),
        )

        if self.status not in (
            self.ALLOWED,
            self.DENIED,
        ):
            raise ValueError(
                "status must be ALLOWED or DENIED"
            )

    @property
    def allowed(self) -> bool:
        return self.status == self.ALLOWED

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_identity": self.provider_identity,
            "model_identity": self.model_identity,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderGovernancePolicy:
    """
    Immutable explicit allowlist.

    An empty policy denies every provider/model pair.
    """

    allowed_models: tuple[GroundedProviderModelAllowance, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.allowed_models,
            tuple,
        ):
            raise TypeError(
                "allowed_models must be a tuple"
            )
        if any(
            not isinstance(
                item,
                GroundedProviderModelAllowance,
            )
            for item in self.allowed_models
        ):
            raise TypeError(
                "allowed_models must contain only "
                "GroundedProviderModelAllowance values"
            )

        keys = tuple(
            item.identity_key
            for item in self.allowed_models
        )
        if len(
            set(
                keys
            )
        ) != len(keys):
            raise ValueError(
                "allowed provider/model pairs must be unique"
            )

    @property
    def allowed_identity_keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.identity_key
                for item in self.allowed_models
            )
        )

    def assess(
        self,
        *,
        provider_identity: str,
        model_identity: str,
    ) -> GroundedProviderGovernanceAssessment:
        provider = normalize_required_text(
            provider_identity,
            field_name="provider_identity",
            uppercase=True,
        )
        model = normalize_required_text(
            model_identity,
            field_name="model_identity",
        )

        requested_key = (
            f"{provider}:{model}"
        )

        if requested_key in set(
            self.allowed_identity_keys
        ):
            return GroundedProviderGovernanceAssessment(
                provider_identity=provider,
                model_identity=model,
                status="ALLOWED",
                reason=(
                    "provider/model pair is explicitly present "
                    "in the governance allowlist"
                ),
            )

        return GroundedProviderGovernanceAssessment(
            provider_identity=provider,
            model_identity=model,
            status="DENIED",
            reason=(
                "provider/model pair is not explicitly present "
                "in the governance allowlist"
            ),
        )

    def require_allowed(
        self,
        *,
        provider_identity: str,
        model_identity: str,
    ) -> GroundedProviderGovernanceAssessment:
        assessment = self.assess(
            provider_identity=provider_identity,
            model_identity=model_identity,
        )
        if not assessment.allowed:
            raise PermissionError(
                "provider/model execution is not allowed by governance policy: "
                f"{assessment.provider_identity}:{assessment.model_identity}"
            )
        return assessment

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_models": [
                item.to_dict()
                for item in sorted(
                    self.allowed_models,
                    key=lambda value: value.identity_key,
                )
            ]
        }

"""
Stable application-level failure contract.

External adapters (CLI, HTTP, UI) should depend on these categories rather
than on provider, persistence, or Python built-in exception types.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedAIApplicationFailureDetails:
    category: str
    code: str
    message: str

    def __post_init__(self) -> None:
        for field_name in (
            "category",
            "code",
            "message",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                    uppercase=(
                        field_name in {"category", "code"}
                    ),
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "code": self.code,
            "message": self.message,
        }


class GroundedAIApplicationError(Exception):
    """Stable application-level exception."""

    def __init__(
        self,
        *,
        category: str,
        code: str,
        message: str,
    ) -> None:
        self.details = GroundedAIApplicationFailureDetails(
            category=category,
            code=code,
            message=message,
        )
        super().__init__(
            self.details.message
        )

    @property
    def category(self) -> str:
        return self.details.category

    @property
    def code(self) -> str:
        return self.details.code

    def to_dict(self) -> dict[str, Any]:
        return self.details.to_dict()


def map_application_failure(
    exc: Exception,
) -> GroundedAIApplicationError:
    if isinstance(
        exc,
        GroundedAIApplicationError,
    ):
        return exc

    if isinstance(
        exc,
        PermissionError,
    ):
        return GroundedAIApplicationError(
            category="POLICY_DENIED",
            code="APPLICATION_POLICY_DENIED",
            message=str(exc),
        )

    if isinstance(
        exc,
        (TypeError, ValueError, KeyError, LookupError),
    ):
        return GroundedAIApplicationError(
            category="INVALID_REQUEST",
            code="APPLICATION_INVALID_REQUEST",
            message=str(exc),
        )

    if isinstance(
        exc,
        RuntimeError,
    ):
        return GroundedAIApplicationError(
            category="EXECUTION_FAILED",
            code="APPLICATION_EXECUTION_FAILED",
            message=str(exc),
        )

    return GroundedAIApplicationError(
        category="INTERNAL_ERROR",
        code="APPLICATION_INTERNAL_ERROR",
        message="grounded AI application execution failed",
    )

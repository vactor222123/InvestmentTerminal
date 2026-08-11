"""
Framework-neutral API adapter over the grounded AI application service.

This module defines request/response DTOs and one synchronous adapter. It owns
no HTTP server, routing framework, sockets, authentication middleware, or JSON
transport implementation.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.application.errors import (
    GroundedAIApplicationError,
)
from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
    GroundedAIApplicationService,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedAIAPIRequest:
    request_id: str
    query: str
    subjects: tuple[str, ...] = ()
    max_items: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            normalize_required_text(
                self.request_id,
                field_name="request_id",
            ),
        )
        object.__setattr__(
            self,
            "query",
            normalize_required_text(
                self.query,
                field_name="query",
            ),
        )

        if not isinstance(
            self.subjects,
            tuple,
        ):
            raise TypeError(
                "subjects must be a tuple"
            )

        normalized_subjects = tuple(
            normalize_required_text(
                subject,
                field_name="subject",
            )
            for subject in self.subjects
        )
        if len(
            set(normalized_subjects)
        ) != len(normalized_subjects):
            raise ValueError(
                "subjects must be unique"
            )
        object.__setattr__(
            self,
            "subjects",
            normalized_subjects,
        )

        if self.max_items is not None and (
            isinstance(
                self.max_items,
                bool,
            )
            or not isinstance(
                self.max_items,
                int,
            )
            or self.max_items <= 0
        ):
            raise ValueError(
                "max_items must be a positive integer or None"
            )

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
    ) -> "GroundedAIAPIRequest":
        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "payload must be a dictionary"
            )

        allowed = {
            "request_id",
            "query",
            "subjects",
            "max_items",
        }
        unknown = set(
            payload
        ) - allowed
        if unknown:
            raise ValueError(
                "unknown API request fields: "
                + ", ".join(
                    sorted(unknown)
                )
            )

        raw_subjects = payload.get(
            "subjects",
            (),
        )
        if isinstance(
            raw_subjects,
            list,
        ):
            raw_subjects = tuple(
                raw_subjects
            )

        return cls(
            request_id=payload.get(
                "request_id",
                "",
            ),
            query=payload.get(
                "query",
                "",
            ),
            subjects=raw_subjects,
            max_items=payload.get(
                "max_items"
            ),
        )

    def to_application_request(
        self,
    ) -> GroundedAIApplicationRequest:
        return GroundedAIApplicationRequest(
            request_id=self.request_id,
            user_query=self.query,
            subject_keys=self.subjects,
            max_items=self.max_items,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "request_id": self.request_id,
            "query": self.query,
            "subjects": list(
                self.subjects
            ),
        }
        if self.max_items is not None:
            data["max_items"] = (
                self.max_items
            )
        return data


@dataclass(frozen=True, slots=True)
class GroundedAIAPIResponse:
    status: str
    request_id: str
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def __post_init__(self) -> None:
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
            "request_id",
            normalize_required_text(
                self.request_id,
                field_name="request_id",
            ),
        )

        if self.status not in {
            "SUCCESS",
            "ERROR",
        }:
            raise ValueError(
                "status must be SUCCESS or ERROR"
            )

        if self.status == "SUCCESS":
            if not isinstance(
                self.data,
                dict,
            ):
                raise TypeError(
                    "successful API response requires data"
                )
            if self.error is not None:
                raise ValueError(
                    "successful API response cannot contain error"
                )
        else:
            if not isinstance(
                self.error,
                dict,
            ):
                raise TypeError(
                    "error API response requires error"
                )
            if self.data is not None:
                raise ValueError(
                    "error API response cannot contain data"
                )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "request_id": self.request_id,
        }
        if self.data is not None:
            result["data"] = (
                self.data
            )
        if self.error is not None:
            result["error"] = (
                self.error
            )
        return result


class GroundedAIAPIAdapter:
    """Framework-neutral synchronous API adapter."""

    def __init__(
        self,
        *,
        application_service: GroundedAIApplicationService,
    ) -> None:
        if not isinstance(
            application_service,
            GroundedAIApplicationService,
        ):
            raise TypeError(
                "application_service must be a "
                "GroundedAIApplicationService"
            )
        self._application_service = (
            application_service
        )

    def handle(
        self,
        request: GroundedAIAPIRequest,
    ) -> GroundedAIAPIResponse:
        if not isinstance(
            request,
            GroundedAIAPIRequest,
        ):
            raise TypeError(
                "request must be a GroundedAIAPIRequest"
            )

        try:
            result = (
                self._application_service.execute(
                    request.to_application_request()
                )
            )
        except GroundedAIApplicationError as exc:
            return GroundedAIAPIResponse(
                status="ERROR",
                request_id=request.request_id,
                error=exc.to_dict(),
            )

        return GroundedAIAPIResponse(
            status="SUCCESS",
            request_id=request.request_id,
            data=result.to_dict(),
        )

"""
Provider-neutral transport contract for grounded AI provider integrations.

This module defines request/response envelopes and transport failure
classification only. It performs no real network I/O.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class GroundedProviderTransportRequest:
    """Immutable provider-neutral HTTP-like request envelope."""

    request_id: str
    method: str
    url: str
    headers: tuple[tuple[str, str], ...]
    body: str
    timeout_seconds: float

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "method",
            "url",
            "body",
        ):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                ),
            )

        object.__setattr__(
            self,
            "method",
            self.method.upper(),
        )

        if not isinstance(
            self.headers,
            tuple,
        ):
            raise TypeError(
                "headers must be a tuple"
            )

        normalized_headers = []
        for item in self.headers:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
            ):
                raise TypeError(
                    "headers must contain (name, value) tuples"
                )
            name = normalize_required_text(
                item[0],
                field_name="header_name",
            )
            value = normalize_required_text(
                item[1],
                field_name="header_value",
            )
            normalized_headers.append(
                (
                    name,
                    value,
                )
            )

        names = [
            name.lower()
            for name, _ in normalized_headers
        ]
        if len(set(names)) != len(names):
            raise ValueError(
                "header names must be unique case-insensitively"
            )

        object.__setattr__(
            self,
            "headers",
            tuple(
                normalized_headers
            ),
        )

        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(
                self.timeout_seconds,
                (int, float),
            )
            or self.timeout_seconds <= 0
        ):
            raise ValueError(
                "timeout_seconds must be a positive number"
            )
        object.__setattr__(
            self,
            "timeout_seconds",
            float(
                self.timeout_seconds
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "method": self.method,
            "url": self.url,
            "headers": [
                {
                    "name": name,
                    "value": value,
                }
                for name, value in self.headers
            ],
            "body": self.body,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderTransportResponse:
    """Immutable provider-neutral transport response."""

    request_id: str
    status_code: int
    headers: tuple[tuple[str, str], ...]
    body: str

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
            "body",
            normalize_required_text(
                self.body,
                field_name="body",
            ),
        )

        if (
            isinstance(self.status_code, bool)
            or not isinstance(
                self.status_code,
                int,
            )
            or not 100 <= self.status_code <= 599
        ):
            raise ValueError(
                "status_code must be an HTTP status code"
            )

        if not isinstance(
            self.headers,
            tuple,
        ):
            raise TypeError(
                "headers must be a tuple"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status_code": self.status_code,
            "headers": [
                {
                    "name": name,
                    "value": value,
                }
                for name, value in self.headers
            ],
            "body": self.body,
        }


@dataclass(frozen=True, slots=True)
class GroundedProviderTransportFailure(Exception):
    """Typed provider-neutral transport failure."""

    kind: str
    message: str
    retryable: bool

    TIMEOUT = "TIMEOUT"
    RETRYABLE = "RETRYABLE"
    TERMINAL = "TERMINAL"

    def __post_init__(self) -> None:
        if self.kind not in (
            self.TIMEOUT,
            self.RETRYABLE,
            self.TERMINAL,
        ):
            raise ValueError(
                "kind must be TIMEOUT, RETRYABLE, or TERMINAL"
            )

        object.__setattr__(
            self,
            "message",
            normalize_required_text(
                self.message,
                field_name="message",
            ),
        )

        expected_retryable = (
            self.kind
            in (
                self.TIMEOUT,
                self.RETRYABLE,
            )
        )
        if self.retryable is not expected_retryable:
            raise ValueError(
                "retryable flag must match failure kind"
            )

        Exception.__init__(
            self,
            self.message,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "retryable": self.retryable,
        }


class GroundedProviderTransport(ABC):
    """Abstract provider-neutral transport boundary."""

    @abstractmethod
    def send(
        self,
        request: GroundedProviderTransportRequest,
    ) -> GroundedProviderTransportResponse:
        """Send one provider request or raise GroundedProviderTransportFailure."""


class StaticGroundedProviderTransport(
    GroundedProviderTransport
):
    """Deterministic test/reference transport with no network I/O."""

    def __init__(
        self,
        *,
        response: GroundedProviderTransportResponse | None = None,
        failure: GroundedProviderTransportFailure | None = None,
    ) -> None:
        if (
            response is None
            and failure is None
        ):
            raise ValueError(
                "response or failure must be provided"
            )
        if (
            response is not None
            and failure is not None
        ):
            raise ValueError(
                "response and failure are mutually exclusive"
            )

        self._response = response
        self._failure = failure

    def send(
        self,
        request: GroundedProviderTransportRequest,
    ) -> GroundedProviderTransportResponse:
        if not isinstance(
            request,
            GroundedProviderTransportRequest,
        ):
            raise TypeError(
                "request must be a GroundedProviderTransportRequest"
            )

        if self._failure is not None:
            raise self._failure

        assert self._response is not None

        if (
            self._response.request_id
            != request.request_id
        ):
            raise ValueError(
                "transport response request_id must match request request_id"
            )

        return self._response

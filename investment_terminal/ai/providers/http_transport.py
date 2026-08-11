"""
Real synchronous HTTP transport using Python's standard library.

This module is provider-neutral. It maps HTTP/network failures into the
canonical GroundedProviderTransportFailure taxonomy and parses Retry-After
metadata at the HTTP boundary.
"""

from datetime import timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import socket
from urllib import error, request as urllib_request

from investment_terminal.ai.providers.clock import (
    GroundedProviderClock,
    SystemGroundedProviderClock,
)
from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportRequest,
    GroundedProviderTransportResponse,
)


class UrllibGroundedProviderTransport(
    GroundedProviderTransport
):
    RETRYABLE_STATUS_CODES = {
        408,
        425,
        429,
    }

    def __init__(
        self,
        *,
        clock: GroundedProviderClock | None = None,
    ) -> None:
        active_clock = (
            clock
            if clock is not None
            else SystemGroundedProviderClock()
        )
        if not isinstance(
            active_clock,
            GroundedProviderClock,
        ):
            raise TypeError(
                "clock must be a GroundedProviderClock"
            )
        self._clock = active_clock

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

        raw_request = urllib_request.Request(
            url=request.url,
            data=request.body.encode("utf-8"),
            headers={
                name: value
                for name, value in request.headers
            },
            method=request.method,
        )

        try:
            with urllib_request.urlopen(
                raw_request,
                timeout=request.timeout_seconds,
            ) as response:
                status_code = int(
                    response.status
                )
                body = response.read().decode(
                    "utf-8"
                )
                headers = tuple(
                    (
                        name,
                        value,
                    )
                    for name, value in response.headers.items()
                )

        except error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            retry_after_seconds = self._parse_retry_after(
                exc.headers.get("Retry-After")
                if exc.headers is not None
                else None
            )
            self._raise_for_http_status(
                status_code=exc.code,
                body=body,
                retry_after_seconds=retry_after_seconds,
            )
            raise RuntimeError(
                "unreachable HTTP error classification"
            )

        except socket.timeout as exc:
            raise GroundedProviderTransportFailure(
                kind="TIMEOUT",
                message="provider request timed out",
                retryable=True,
            ) from exc

        except TimeoutError as exc:
            raise GroundedProviderTransportFailure(
                kind="TIMEOUT",
                message="provider request timed out",
                retryable=True,
            ) from exc

        except error.URLError as exc:
            if isinstance(
                exc.reason,
                socket.timeout,
            ):
                raise GroundedProviderTransportFailure(
                    kind="TIMEOUT",
                    message="provider request timed out",
                    retryable=True,
                ) from exc

            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message="provider network transport failed",
                retryable=True,
            ) from exc

        self._raise_for_http_status(
            status_code=status_code,
            body=body,
            retry_after_seconds=None,
        )

        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=status_code,
            headers=headers,
            body=body,
        )

    def _parse_retry_after(
        self,
        value: str | None,
    ) -> Decimal | None:
        delta = self._parse_retry_after_delta_seconds(
            value
        )
        if delta is not None:
            return delta

        return self._parse_retry_after_http_date(
            value
        )

    @staticmethod
    def _parse_retry_after_delta_seconds(
        value: str | None,
    ) -> Decimal | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = Decimal(stripped)
        except InvalidOperation:
            return None
        if not parsed.is_finite() or parsed < 0:
            return None
        return parsed

    def _parse_retry_after_http_date(
        self,
        value: str | None,
    ) -> Decimal | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None

        try:
            target = parsedate_to_datetime(
                stripped
            )
        except (TypeError, ValueError, OverflowError):
            return None

        if target is None:
            return None

        if target.tzinfo is None:
            target = target.replace(
                tzinfo=timezone.utc
            )
        else:
            target = target.astimezone(
                timezone.utc
            )

        now = self._clock.now_utc()
        if now.tzinfo is None:
            raise ValueError(
                "clock must return a timezone-aware UTC datetime"
            )
        now = now.astimezone(
            timezone.utc
        )

        delay = Decimal(
            str(
                max(
                    0.0,
                    (
                        target - now
                    ).total_seconds(),
                )
            )
        )
        return delay

    @classmethod
    def _raise_for_http_status(
        cls,
        *,
        status_code: int,
        body: str,
        retry_after_seconds: Decimal | None = None,
    ) -> None:
        if 200 <= status_code <= 299:
            return

        message = (
            f"provider HTTP {status_code}"
        )
        if body.strip():
            message += (
                ": "
                + body.strip()[:500]
            )

        if (
            status_code in cls.RETRYABLE_STATUS_CODES
            or 500 <= status_code <= 599
        ):
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message=message,
                retryable=True,
                retry_after_seconds=retry_after_seconds,
            )

        raise GroundedProviderTransportFailure(
            kind="TERMINAL",
            message=message,
            retryable=False,
        )

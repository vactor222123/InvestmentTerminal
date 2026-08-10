"""
Real synchronous HTTP transport using Python's standard library.

This module is provider-neutral. It maps HTTP/network failures into the
canonical GroundedProviderTransportFailure taxonomy.
"""

import socket
from urllib import error, request as urllib_request

from investment_terminal.ai.providers.transport import (
    GroundedProviderTransport,
    GroundedProviderTransportFailure,
    GroundedProviderTransportRequest,
    GroundedProviderTransportResponse,
)


class UrllibGroundedProviderTransport(
    GroundedProviderTransport
):
    """Synchronous real HTTP transport backed by urllib.request."""

    RETRYABLE_STATUS_CODES = {
        408,
        425,
        429,
    }

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
            data=request.body.encode(
                "utf-8"
            ),
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
            self._raise_for_http_status(
                status_code=exc.code,
                body=body,
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
        )

        return GroundedProviderTransportResponse(
            request_id=request.request_id,
            status_code=status_code,
            headers=headers,
            body=body,
        )

    @classmethod
    def _raise_for_http_status(
        cls,
        *,
        status_code: int,
        body: str,
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
            status_code
            in cls.RETRYABLE_STATUS_CODES
            or 500 <= status_code <= 599
        ):
            raise GroundedProviderTransportFailure(
                kind="RETRYABLE",
                message=message,
                retryable=True,
            )

        raise GroundedProviderTransportFailure(
            kind="TERMINAL",
            message=message,
            retryable=False,
        )

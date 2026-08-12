"""
Inbound request-size guardrails for the server runtime.

The policy is evaluated after authentication but before JSON decoding,
application execution, or provider execution.
"""

from dataclasses import dataclass

from fastapi import Request


class GroundedAIServerRequestTooLargeError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class GroundedAIServerRequestLimitPolicy:
    max_body_bytes: int = 65536

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_body_bytes, bool)
            or not isinstance(self.max_body_bytes, int)
            or self.max_body_bytes <= 0
        ):
            raise ValueError(
                "max_body_bytes must be a positive integer"
            )

    async def read_body(
        self,
        request: Request,
    ) -> bytes:
        content_length = request.headers.get(
            "content-length"
        )
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = None
            if (
                declared is not None
                and declared > self.max_body_bytes
            ):
                raise GroundedAIServerRequestTooLargeError(
                    "request body exceeds configured maximum"
                )

        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > self.max_body_bytes:
                raise GroundedAIServerRequestTooLargeError(
                    "request body exceeds configured maximum"
                )

        return bytes(body)

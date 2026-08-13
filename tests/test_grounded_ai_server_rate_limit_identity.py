from hashlib import sha256

import pytest

from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentityDeriver,
)


def test_identity_derivation_is_deterministic_and_opaque() -> None:
    raw = "server-secret"

    identity = GroundedAIServerRateLimitIdentityDeriver().derive(
        raw
    )

    assert str(identity) == sha256(
        raw.encode("utf-8")
    ).hexdigest()
    assert raw not in str(identity)


def test_identity_derivation_normalizes_outer_whitespace() -> None:
    deriver = GroundedAIServerRateLimitIdentityDeriver()

    assert deriver.derive(
        " server-secret "
    ) == deriver.derive(
        "server-secret"
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
    ],
)
def test_identity_derivation_rejects_empty_values(
    value,
) -> None:
    with pytest.raises(
        ValueError,
        match="non-empty",
    ):
        GroundedAIServerRateLimitIdentityDeriver().derive(
            value
        )

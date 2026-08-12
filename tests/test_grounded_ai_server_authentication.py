from investment_terminal.server.authentication import (
    GroundedAIServerAPIKeyAuthenticator,
)


def test_authenticator_accepts_exact_api_key() -> None:
    authenticator = GroundedAIServerAPIKeyAuthenticator(
        expected_api_key="secret-value",
    )

    assert authenticator.authenticate(
        "secret-value"
    )


def test_authenticator_rejects_missing_empty_and_wrong_api_key() -> None:
    authenticator = GroundedAIServerAPIKeyAuthenticator(
        expected_api_key="secret-value",
    )

    assert not authenticator.authenticate(
        None
    )
    assert not authenticator.authenticate(
        ""
    )
    assert not authenticator.authenticate(
        "wrong-value"
    )

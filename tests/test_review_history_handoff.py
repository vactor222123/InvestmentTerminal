from investment_terminal.review.history_handoff import (
    prepare_review_package_history_handoff,
)


def test_review_history_handoff_is_explicit_boundary():
    payload = object()

    assert prepare_review_package_history_handoff(payload) is payload

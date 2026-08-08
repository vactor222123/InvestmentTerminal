"""
Tests for HistoricalDeploymentComparator.
"""

import pytest

from investment_terminal.history.historical_deployment_comparator import (
    HistoricalDeploymentComparator,
)
from investment_terminal.history.historical_deployment_models import (
    HistoricalDeployment,
)


FIRST_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
SECOND_ID = (
    "f9b7adca-2f2b-47a4-901d-05ca37c445df"
)


def deployment(
    snapshot_id: str,
    key: str,
    *,
    amount: float | None = 500.0,
    share: float | None = 0.25,
    reason: str | None = "Core",
    payload: dict | None = None,
) -> HistoricalDeployment:
    return HistoricalDeployment(
        snapshot_id=snapshot_id,
        deployment_key=key,
        amount=amount,
        share=share,
        reason=reason,
        payload=(
            payload
            if payload is not None
            else {
                "bucket": key,
                "reason": reason,
            }
        ),
    )


def test_comparator_detects_added_removed_changed_and_unchanged() -> None:
    result = HistoricalDeploymentComparator().compare(
        previous=(
            deployment(
                FIRST_ID,
                "DROP",
            ),
            deployment(
                FIRST_ID,
                "KEEP",
            ),
            deployment(
                FIRST_ID,
                "MOVE",
            ),
        ),
        current=(
            deployment(
                SECOND_ID,
                "KEEP",
            ),
            deployment(
                SECOND_ID,
                "MOVE",
                amount=700.0,
                share=0.35,
            ),
            deployment(
                SECOND_ID,
                "NEW",
            ),
        ),
    )

    assert [
        item.deployment_key
        for item in result
    ] == [
        "DROP",
        "KEEP",
        "MOVE",
        "NEW",
    ]

    by_key = {
        item.deployment_key: item
        for item in result
    }

    assert by_key[
        "DROP"
    ].change_type == "REMOVED"
    assert by_key[
        "KEEP"
    ].change_type == "UNCHANGED"
    assert by_key[
        "MOVE"
    ].change_type == "CHANGED"
    assert by_key[
        "NEW"
    ].change_type == "ADDED"

    assert by_key[
        "MOVE"
    ].amount.absolute_change == 200.0
    assert by_key[
        "MOVE"
    ].share.absolute_change == pytest.approx(
        0.1
    )


def test_reason_change_marks_deployment_changed() -> None:
    result = HistoricalDeploymentComparator().compare(
        previous=(
            deployment(
                FIRST_ID,
                "CORE",
                reason="Old",
            ),
        ),
        current=(
            deployment(
                SECOND_ID,
                "CORE",
                reason="New",
            ),
        ),
    )

    change = result[
        0
    ]

    assert change.change_type == "CHANGED"
    assert change.previous[
        "reason"
    ] == "Old"
    assert change.current[
        "reason"
    ] == "New"


def test_payload_change_marks_deployment_changed() -> None:
    result = HistoricalDeploymentComparator().compare(
        previous=(
            deployment(
                FIRST_ID,
                "CORE",
                payload={
                    "bucket": "CORE",
                    "tag": "old",
                },
            ),
        ),
        current=(
            deployment(
                SECOND_ID,
                "CORE",
                payload={
                    "bucket": "CORE",
                    "tag": "new",
                },
            ),
        ),
    )

    assert result[
        0
    ].change_type == "CHANGED"


def test_optional_numbers_keep_absent_value_semantics() -> None:
    result = HistoricalDeploymentComparator().compare(
        previous=(
            deployment(
                FIRST_ID,
                "CORE",
                amount=None,
                share=None,
            ),
        ),
        current=(
            deployment(
                SECOND_ID,
                "CORE",
                amount=400.0,
                share=0.4,
            ),
        ),
    )

    change = result[
        0
    ]

    assert change.amount.previous is None
    assert change.amount.current == 400.0
    assert change.amount.absolute_change is None
    assert change.share.percentage_change is None


def test_different_keys_are_not_implicitly_matched() -> None:
    result = HistoricalDeploymentComparator().compare(
        previous=(
            deployment(
                FIRST_ID,
                "OLD",
            ),
        ),
        current=(
            deployment(
                SECOND_ID,
                "NEW",
            ),
        ),
    )

    assert [
        (
            item.deployment_key,
            item.change_type,
        )
        for item in result
    ] == [
        (
            "NEW",
            "ADDED",
        ),
        (
            "OLD",
            "REMOVED",
        ),
    ]


def test_comparator_rejects_duplicate_keys() -> None:
    duplicate = deployment(
        FIRST_ID,
        "CORE",
    )

    with pytest.raises(
        ValueError,
        match="duplicate deployment_key CORE",
    ):
        HistoricalDeploymentComparator().compare(
            previous=(
                duplicate,
                duplicate,
            ),
            current=(),
        )

"""
Tests for HistoricalTimelineEvent.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from investment_terminal.history.historical_timeline_models import (
    HistoricalTimelineEvent,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)


def create_event(
    **overrides,
) -> HistoricalTimelineEvent:
    values = {
        "event_id": 1,
        "snapshot_id": SNAPSHOT_ID,
        "event_type": "HOLDING_RECORDED",
        "occurred_at": datetime(
            2026,
            8,
            3,
            17,
            35,
            tzinfo=timezone.utc,
        ),
        "subject_key": "IE00B4L5Y983",
        "payload": {
            "symbol": "WORLD",
            "weight": 0.5,
            "tags": [
                "CORE",
                "LONG_TERM",
            ],
        },
    }
    values.update(
        overrides
    )

    return HistoricalTimelineEvent(
        **values
    )


def test_timeline_event_normalizes_and_serializes() -> None:
    event = create_event(
        snapshot_id=SNAPSHOT_ID.upper(),
        event_type=" holding_recorded ",
        subject_key=" IE00B4L5Y983 ",
    )

    assert event.snapshot_id == SNAPSHOT_ID
    assert event.event_type == "HOLDING_RECORDED"
    assert event.subject_key == "IE00B4L5Y983"
    assert event.to_dict() == {
        "event_id": 1,
        "snapshot_id": SNAPSHOT_ID,
        "event_type": "HOLDING_RECORDED",
        "occurred_at": (
            "2026-08-03T17:35:00+00:00"
        ),
        "subject_key": "IE00B4L5Y983",
        "payload": {
            "symbol": "WORLD",
            "tags": [
                "CORE",
                "LONG_TERM",
            ],
            "weight": 0.5,
        },
    }


def test_timeline_event_accepts_missing_subject_key() -> None:
    event = create_event(
        subject_key=None
    )

    assert event.subject_key is None


def test_timeline_event_is_immutable() -> None:
    event = create_event()

    with pytest.raises(
        FrozenInstanceError,
    ):
        event.event_type = "CHANGED"  # type: ignore[misc]

    with pytest.raises(
        TypeError,
    ):
        event.payload["symbol"] = "CHANGED"  # type: ignore[index]


def test_timeline_event_detaches_nested_payload() -> None:
    payload = {
        "nested": {
            "values": [
                1,
                2,
            ]
        }
    }

    event = create_event(
        payload=payload
    )
    payload["nested"]["values"].append(3)

    assert event.to_dict()["payload"] == {
        "nested": {
            "values": [
                1,
                2,
            ]
        }
    }


@pytest.mark.parametrize(
    "event_id",
    (
        0,
        -1,
        True,
        1.5,
        "1",
    ),
)
def test_timeline_event_rejects_invalid_event_id(
    event_id,
) -> None:
    with pytest.raises(
        ValueError,
        match="event_id must be a positive integer",
    ):
        create_event(
            event_id=event_id
        )


def test_timeline_event_rejects_invalid_snapshot_id() -> None:
    with pytest.raises(
        ValueError,
        match="snapshot_id must be a valid UUID string",
    ):
        create_event(
            snapshot_id="not-a-uuid"
        )


@pytest.mark.parametrize(
    "event_type",
    (
        "",
        "   ",
        None,
    ),
)
def test_timeline_event_rejects_invalid_event_type(
    event_type,
) -> None:
    with pytest.raises(
        ValueError,
        match="event_type must be a non-empty string",
    ):
        create_event(
            event_type=event_type
        )


def test_timeline_event_rejects_naive_occurred_at() -> None:
    with pytest.raises(
        ValueError,
        match="occurred_at must be timezone-aware",
    ):
        create_event(
            occurred_at=datetime(
                2026,
                8,
                3,
                17,
                35,
            )
        )


def test_timeline_event_rejects_non_datetime_occurred_at() -> None:
    with pytest.raises(
        TypeError,
        match="occurred_at must be a datetime",
    ):
        create_event(
            occurred_at="2026-08-03T17:35:00+00:00"
        )


def test_timeline_event_rejects_blank_subject_key() -> None:
    with pytest.raises(
        ValueError,
        match="subject_key must be a non-empty string",
    ):
        create_event(
            subject_key="   "
        )


@pytest.mark.parametrize(
    "payload",
    (
        [],
        "payload",
        None,
    ),
)
def test_timeline_event_rejects_non_object_payload(
    payload,
) -> None:
    with pytest.raises(
        ValueError,
        match="payload must be a JSON object",
    ):
        create_event(
            payload=payload
        )


def test_timeline_event_rejects_non_json_payload_value() -> None:
    with pytest.raises(
        ValueError,
        match="payload must contain JSON-compatible values",
    ):
        create_event(
            payload={
                "bad": object(),
            }
        )


def test_timeline_event_rejects_non_finite_payload_number() -> None:
    with pytest.raises(
        ValueError,
        match="payload must contain JSON-compatible values",
    ):
        create_event(
            payload={
                "bad": float("nan"),
            }
        )

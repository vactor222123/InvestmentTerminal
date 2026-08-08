"""
Tests for safe historical replay request and result contracts.
"""

from dataclasses import FrozenInstanceError

import pytest

from investment_terminal.history.historical_replay_models import (
    HistoricalReplayRequest,
    HistoricalReplayResult,
)


SNAPSHOT_ID = (
    "2f132e09-38c9-4471-bb48-875b4f9ec8e8"
)
CHECKSUM = "a" * 64


def test_exact_replay_request_normalizes() -> None:
    request = HistoricalReplayRequest(
        snapshot_id=SNAPSHOT_ID.upper(),
        mode=" exact_archived_package ",
    )

    assert request.snapshot_id == SNAPSHOT_ID
    assert request.mode == "EXACT_ARCHIVED_PACKAGE"
    assert request.is_supported
    assert request.is_exact_evidence_request
    assert request.to_dict() == {
        "snapshot_id": SNAPSHOT_ID,
        "mode": "EXACT_ARCHIVED_PACKAGE",
        "supported": True,
    }


def test_normalized_view_request_is_supported() -> None:
    request = HistoricalReplayRequest(
        snapshot_id=SNAPSHOT_ID,
        mode="NORMALIZED_HISTORICAL_VIEW",
    )

    assert request.is_supported
    assert not request.is_exact_evidence_request


def test_current_code_recalculation_is_defined_but_unsupported() -> None:
    request = HistoricalReplayRequest(
        snapshot_id=SNAPSHOT_ID,
        mode="CURRENT_CODE_RECALCULATION",
    )

    assert not request.is_supported
    assert request.mode in request.DEFINED_MODES
    assert request.mode not in request.SUPPORTED_MODES


def test_request_rejects_unknown_mode() -> None:
    with pytest.raises(
        ValueError,
        match="mode must be one of",
    ):
        HistoricalReplayRequest(
            snapshot_id=SNAPSHOT_ID,
            mode="UNKNOWN",
        )


def test_exact_result_preserves_provenance_and_detaches_payload() -> None:
    payload = {
        "schema_version": "1.0",
        "sections": {
            "items": [
                1,
                2,
            ]
        },
    }

    result = HistoricalReplayResult(
        snapshot_id=SNAPSHOT_ID.upper(),
        mode=" exact_archived_package ",
        package_schema_version=" 1.0 ",
        evidence_checksum_sha256=CHECKSUM.upper(),
        payload=payload,
        warnings=(),
    )

    payload[
        "sections"
    ][
        "items"
    ].append(
        3
    )

    assert result.snapshot_id == SNAPSHOT_ID
    assert result.evidence_checksum_sha256 == CHECKSUM
    assert result.is_exact_archived_evidence
    assert not result.is_normalized_view
    assert result.to_dict()[
        "payload"
    ][
        "sections"
    ][
        "items"
    ] == [
        1,
        2,
    ]


def test_normalized_result_exposes_warning_without_claiming_exact_payload() -> None:
    result = HistoricalReplayResult(
        snapshot_id=SNAPSHOT_ID,
        mode="NORMALIZED_HISTORICAL_VIEW",
        package_schema_version="1.0",
        evidence_checksum_sha256=CHECKSUM,
        payload={
            "snapshot": {
                "snapshot_id": SNAPSHOT_ID,
            }
        },
        warnings=(
            "Normalized SQLite projection; archive remains canonical evidence",
        ),
    )

    data = result.to_dict()

    assert result.is_normalized_view
    assert not result.is_exact_archived_evidence
    assert data[
        "exact_archived_evidence"
    ] is False
    assert data[
        "warnings"
    ] == [
        "Normalized SQLite projection; archive remains canonical evidence",
    ]


def test_result_rejects_current_code_recalculation() -> None:
    with pytest.raises(
        ValueError,
        match="supports only implemented replay modes",
    ):
        HistoricalReplayResult(
            snapshot_id=SNAPSHOT_ID,
            mode="CURRENT_CODE_RECALCULATION",
            package_schema_version="1.0",
            evidence_checksum_sha256=CHECKSUM,
            payload={},
        )


def test_result_rejects_invalid_checksum() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "checksum_sha256 must contain "
            "64 hexadecimal characters"
        ),
    ):
        HistoricalReplayResult(
            snapshot_id=SNAPSHOT_ID,
            mode="EXACT_ARCHIVED_PACKAGE",
            package_schema_version="1.0",
            evidence_checksum_sha256="bad",
            payload={},
        )


def test_result_rejects_non_json_payload() -> None:
    with pytest.raises(
        ValueError,
        match="payload must contain JSON-compatible values",
    ):
        HistoricalReplayResult(
            snapshot_id=SNAPSHOT_ID,
            mode="EXACT_ARCHIVED_PACKAGE",
            package_schema_version="1.0",
            evidence_checksum_sha256=CHECKSUM,
            payload={
                "invalid": {
                    1,
                    2,
                }
            },
        )


def test_models_are_frozen() -> None:
    request = HistoricalReplayRequest(
        snapshot_id=SNAPSHOT_ID,
        mode="EXACT_ARCHIVED_PACKAGE",
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        request.mode = "NORMALIZED_HISTORICAL_VIEW"  # type: ignore[misc]

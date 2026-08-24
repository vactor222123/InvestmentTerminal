from datetime import datetime, timezone

import pytest

from investment_terminal.cli.xnys_session_evidence import build_document


def test_bounded_xnys_document_has_official_window_and_provenance():
    document = build_document(datetime(2026, 8, 24, tzinfo=timezone.utc))

    assert document["calendar"] == {
        "calendar_id": "XNYS",
        "version": 1,
        "timezone": "America/New_York",
        "source": "NYSE_GROUP_CALENDAR",
    }
    assert len(document["sessions"]) == 1254
    assert document["sessions"][0]["session_key"] == "XNYS:2021-08-19"
    assert document["sessions"][-1]["session_key"] == "XNYS:2026-08-18"
    assert len(document["evidence"]["source_uris"]) == 5
    assert not any(
        item["session_date"] == "2025-01-09"
        for item in document["sessions"]
    )


def test_bounded_xnys_document_rejects_naive_retrieval_time():
    with pytest.raises(ValueError, match="retrieved_at must be timezone-aware"):
        build_document(datetime(2026, 8, 24))

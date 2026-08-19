from datetime import datetime, timezone
import json

import pytest

from investment_terminal.cli.xnas_session_evidence import (
    build_document,
    build_five_year_document,
)
from investment_terminal.history.session_calendar_evidence import (
    verify_session_calendar_evidence,
)


def test_bounded_xnas_document_has_expected_sessions_and_checksum(tmp_path):
    document = build_document(datetime(2026, 8, 19, tzinfo=timezone.utc))
    assert len(document["sessions"]) == 251
    assert document["sessions"][0]["session_date"] == "2025-08-19"
    assert document["sessions"][-1]["session_date"] == "2026-08-18"
    early = next(item for item in document["sessions"]
                 if item["session_date"] == "2025-11-28")
    assert early["closes_at"].endswith("13:00:00-05:00")
    assert not any(item["session_date"] == "2026-07-03"
                   for item in document["sessions"])


def test_five_year_document_preserves_official_exception_and_version():
    document = build_five_year_document(
        datetime(2026, 8, 19, tzinfo=timezone.utc)
    )
    assert document["calendar"]["version"] == 2
    assert document["sessions"][0]["session_date"] == "2021-08-19"
    assert document["sessions"][-1]["session_date"] == "2026-08-18"
    assert not any(
        item["session_date"] == "2025-01-09"
        for item in document["sessions"]
    )
    assert len(document["evidence"]["source_uris"]) == 8


def test_evidence_rejects_primary_source_absent_from_source_list(tmp_path):
    document = build_five_year_document(
        datetime(2026, 8, 19, tzinfo=timezone.utc)
    )
    document["evidence"]["source_uris"].remove(
        document["evidence"]["source_uri"]
    )
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="evidence.source_uri must appear in evidence.source_uris",
    ):
        verify_session_calendar_evidence(path)

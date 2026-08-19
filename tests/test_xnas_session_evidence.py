from datetime import datetime, timezone

from investment_terminal.cli.xnas_session_evidence import build_document


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

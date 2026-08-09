"""
Focused tests for the methodology-aware outcome CLI.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.methodology_outcome_history import (
    ELAPSED_METHODOLOGY,
    SESSION_METHODOLOGY,
    _load_session_calendar,
    _methodology_window_calendar,
    build_argument_parser,
)


def write_calendar(
    tmp_path: Path,
) -> Path:
    path = tmp_path / "xetra_sessions.json"
    path.write_text(
        json.dumps(
            {
                "calendar": {
                    "calendar_id": "XETRA",
                    "version": 1,
                    "timezone": "Europe/Berlin",
                    "source": "LOCAL_JSON_FIXTURE",
                },
                "sessions": [
                    {
                        "session_key": "XETRA:2026-08-10",
                        "session_date": "2026-08-10",
                        "opens_at": "2026-08-10T09:00:00+02:00",
                        "closes_at": "2026-08-10T17:30:00+02:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_elapsed_methodology_is_explicit_and_needs_no_calendar() -> None:
    methodology, window, calendar = _methodology_window_calendar(
        methodology_name=ELAPSED_METHODOLOGY,
        window_value=5,
        session_calendar_path=None,
    )

    assert methodology.identity_key == (
        "ELAPSED_DAYS_EXACT_CLOSE@1"
    )
    assert window.kind == "ELAPSED_DAYS"
    assert window.value == 5
    assert calendar.list_all() == ()


def test_session_methodology_requires_local_calendar(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="required",
    ):
        _methodology_window_calendar(
            methodology_name=SESSION_METHODOLOGY,
            window_value=1,
            session_calendar_path=None,
        )


def test_session_methodology_exposes_calendar_and_selection_identity(
    tmp_path: Path,
) -> None:
    path = write_calendar(
        tmp_path
    )

    methodology, window, calendar = _methodology_window_calendar(
        methodology_name=SESSION_METHODOLOGY,
        window_value=1,
        session_calendar_path=path,
    )

    assert methodology.identity_key == (
        "TRADING_SESSIONS_EXACT_CLOSE@1"
    )
    assert methodology.endpoint_policy.identity_key == (
        "TRADING_SESSION_CLOSE@1"
    )
    assert methodology.evidence_selection_policy.identity_key == (
        "SESSION_CLOSE_EXACT@1"
    )
    assert window.kind == "TRADING_SESSIONS"
    assert calendar.identity.identity_key == "XETRA@1"
    assert calendar.list_all()[0].session_key == (
        "XETRA:2026-08-10"
    )


def test_calendar_loader_preserves_session_provenance(
    tmp_path: Path,
) -> None:
    calendar = _load_session_calendar(
        write_calendar(
            tmp_path
        )
    )

    assert calendar.identity.source == "LOCAL_JSON_FIXTURE"
    session = calendar.list_all()[0]
    assert session.calendar == calendar.identity
    assert session.closes_at.isoformat() == (
        "2026-08-10T17:30:00+02:00"
    )


def test_elapsed_methodology_rejects_unused_calendar(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="not used",
    ):
        _methodology_window_calendar(
            methodology_name=ELAPSED_METHODOLOGY,
            window_value=5,
            session_calendar_path=write_calendar(
                tmp_path
            ),
        )


def test_parser_requires_explicit_methodology() -> None:
    parser = build_argument_parser()

    with pytest.raises(
        SystemExit,
    ):
        parser.parse_args(
            [
                "--recommendation-key",
                "WORLD",
                "--window-value",
                "5",
                "--as-of",
                "2026-08-10T18:00:00+00:00",
            ]
        )


def test_parser_accepts_session_methodology_arguments(
    tmp_path: Path,
) -> None:
    parser = build_argument_parser()
    options = parser.parse_args(
        [
            "--recommendation-key",
            "WORLD",
            "--methodology",
            SESSION_METHODOLOGY,
            "--window-value",
            "1",
            "--session-calendar",
            str(
                write_calendar(
                    tmp_path
                )
            ),
            "--as-of",
            "2026-08-10T18:00:00+00:00",
            "--json",
        ]
    )

    assert options.methodology == SESSION_METHODOLOGY
    assert options.window_value == 1
    assert options.json is True

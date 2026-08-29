from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.models.candle import Candle
from investment_terminal.operations.universe_eligibility_scan import (
    EligibilityScanRequest,
    UniverseEligibilityScanService,
)


END = datetime(2026, 8, 29, tzinfo=timezone.utc)


def _universe(count=3, *, missing_projection=False):
    members = []
    for index in range(count):
        symbol = f"S{index:03d}"
        members.append(
            {
                "source": "NASDAQ_LISTED",
                "source_symbol": symbol,
                "yahoo_symbol": None if missing_projection and index == 0 else symbol,
                "security_name": f"Security {index}",
                "listing_code": "Q",
                "is_etf": False,
            }
        )
    return {
        "schema_version": 1,
        "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256": {
            "NASDAQ_LISTED": "a" * 64,
            "OTHER_LISTED": "b" * 64,
        },
        "members": members,
    }


def _request(count=3, *, missing_projection=False):
    return EligibilityScanRequest.from_universe(
        _universe(count, missing_projection=missing_projection),
        requested_end=END,
    )


def _candle(symbol, day=1, volume=10.0, close=5.0):
    timestamp = END - timedelta(days=day)
    return Candle(
        symbol=symbol,
        resolution="D",
        timestamp=timestamp,
        open_price=close,
        high_price=close,
        low_price=close,
        close_price=close,
        volume=volume,
        currency="USD",
    )


class Client:
    def __init__(self, outcomes=None):
        self.outcomes = outcomes or {}
        self.calls = []

    def get_candles(self, *, symbol, resolution, start, end, currency):
        self.calls.append(symbol)
        outcome = self.outcomes.get(symbol, [_candle(symbol)])
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_request_has_exact_fixed_window_and_stable_checksum():
    first = _request()
    second = EligibilityScanRequest.from_universe(
        dict(reversed(list(_universe().items()))),
        requested_end=END,
    )
    assert first.requested_start == END - timedelta(days=90)
    assert first.checksum == second.checksum
    with pytest.raises(ValueError, match="archive evidence"):
        broken = _universe()
        broken["archive_sha256"]["NASDAQ_LISTED"] = "bad"
        EligibilityScanRequest.from_universe(broken, requested_end=END)


def test_scan_is_bounded_checkpoints_metrics_and_redacts_report():
    request = _request(101)
    checkpoints = []
    client = Client()
    report = UniverseEligibilityScanService(
        client=client,
        checkpoint_writer=checkpoints.append,
        clock=lambda: END,
    ).run(request, max_items=100)

    assert len(client.calls) == 100
    assert len(checkpoints) == 100
    assert report["status"] == "IN_PROGRESS"
    assert report["coverage"]["current_run"] == {
        "attempted_count": 100,
        "provider_request_count": 100,
        "resumed_terminal_count": 0,
    }
    assert report["coverage"]["cumulative"]["pending_count"] == 1
    first = checkpoints[-1]["outcomes"]["NASDAQ_LISTED:S000"]
    assert first["candle_count"] == 1
    assert first["positive_volume_day_count"] == 1
    assert first["median_daily_traded_value"] == 50.0
    serialized = str(report)
    assert "S000" not in serialized
    assert "50.0" not in serialized
    assert "rank" not in report


def test_exact_resume_bypasses_all_terminal_outcomes():
    request = _request(2)
    checkpoints = []
    first_client = Client({"S001": TimeoutError("private provider text")})
    service = UniverseEligibilityScanService(
        client=first_client,
        checkpoint_writer=checkpoints.append,
        clock=lambda: END,
    )
    first = service.run(request)
    assert first["status"] == "COMPLETE"
    assert first["failure_types"] == ["TimeoutError"]

    second_client = Client()
    second = UniverseEligibilityScanService(
        client=second_client,
        checkpoint_writer=lambda payload: pytest.fail("resume rewrote checkpoint"),
        clock=lambda: END,
    ).run(request, checkpoints[-1])
    assert second_client.calls == []
    assert second["coverage"]["current_run"] == {
        "attempted_count": 0,
        "provider_request_count": 0,
        "resumed_terminal_count": 2,
    }


def test_failures_and_missing_projection_are_isolated_terminal_outcomes():
    request = _request(3, missing_projection=True)
    checkpoints = []
    client = Client(
        {
            "S001": [],
            "S002": object(),
        }
    )
    report = UniverseEligibilityScanService(
        client=client,
        checkpoint_writer=checkpoints.append,
        clock=lambda: END,
    ).run(request)
    assert client.calls == ["S001", "S002"]
    assert report["status"] == "COMPLETE"
    assert report["coverage"]["cumulative"] == {
        "member_count": 3,
        "terminal_count": 3,
        "pending_count": 0,
        "success_count": 0,
        "empty_count": 1,
        "failure_count": 1,
        "projection_failure_count": 1,
    }
    assert report["failure_types"] == ["ProjectionUnavailable", "TypeError"]


def test_mismatched_or_invalid_checkpoint_fails_closed():
    request = _request(1)
    checkpoint = {
        "schema_version": 1,
        "request_checksum": "0" * 64,
        "universe_checksum": request.universe_checksum,
        "requested_start": request.requested_start.isoformat(),
        "requested_end": request.requested_end.isoformat(),
        "outcomes": {},
    }
    with pytest.raises(ValueError, match="does not match"):
        UniverseEligibilityScanService(
            client=Client(),
            checkpoint_writer=lambda payload: None,
            clock=lambda: END,
        ).run(request, checkpoint)


def test_out_of_window_and_duplicate_candles_become_failure_categories():
    request = _request(2)
    duplicate = _candle("S001")
    client = Client(
        {
            "S000": [_candle("S000", day=91)],
            "S001": [duplicate, duplicate],
        }
    )
    report = UniverseEligibilityScanService(
        client=client,
        checkpoint_writer=lambda payload: None,
        clock=lambda: END,
    ).run(request)
    assert report["coverage"]["cumulative"]["failure_count"] == 2
    assert report["failure_types"] == ["ValueError"]


@pytest.mark.parametrize("max_items", [0, 101, True, 1.5])
def test_invalid_slice_bound_fails(max_items):
    service = UniverseEligibilityScanService(
        client=Client(),
        checkpoint_writer=lambda payload: None,
        clock=lambda: END,
    )
    with pytest.raises((TypeError, ValueError)):
        service.run(_request(1), max_items=max_items)

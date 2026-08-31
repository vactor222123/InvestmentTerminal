from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.models.candle import Candle
from investment_terminal.operations.universe_eligibility_drain import UniverseEligibilityDrainService
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest


NOW = datetime(2026, 8, 29, tzinfo=timezone.utc)


def request(count):
    universe = {"schema_version": 1, "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256": {"NASDAQ_LISTED": "a"*64, "OTHER_LISTED": "b"*64},
        "members": [{"source": "NASDAQ_LISTED", "source_symbol": f"S{i:03d}",
            "yahoo_symbol": f"S{i:03d}", "security_name": f"Security {i}",
            "listing_code": "Q", "is_etf": False} for i in range(count)]}
    return EligibilityScanRequest.from_universe(universe, requested_end=NOW)


class Client:
    def __init__(self): self.calls = 0
    def get_candles(self, *, symbol, resolution, currency, **kwargs):
        self.calls += 1
        return [Candle(symbol=symbol, resolution=resolution,
            timestamp=NOW-timedelta(days=1), open_price=1, high_price=1,
            low_price=1, close_price=1, volume=1, currency=currency)]


def test_completes_multiple_slices_and_partial_final_slice():
    writes=[]; client=Client()
    report=UniverseEligibilityDrainService(client=client, checkpoint_writer=writes.append,
        clock=lambda:NOW).run(request(205), max_total_items=300)
    assert report["status"] == "COMPLETE"
    assert report["current_run"] == {"slice_count":3,"attempted_count":205,
        "provider_request_count":205}
    assert report["starting_coverage"] == {"terminal_count":0,"pending_count":205}
    assert report["ending_coverage"]["terminal_count"] == 205
    assert "S000" not in str(report)


def test_budget_exhaustion_is_resumable():
    writes=[]; client=Client(); service=UniverseEligibilityDrainService(
        client=client, checkpoint_writer=writes.append, clock=lambda:NOW)
    first=service.run(request(205), max_total_items=150)
    assert first["status"] == "BUDGET_EXHAUSTED"
    second=service.run(request(205), writes[-1], max_total_items=100)
    assert second["status"] == "COMPLETE" and second["current_run"]["attempted_count"] == 55


@pytest.mark.parametrize("value", [0, 20001, True, 1.5])
def test_budget_is_bounded(value):
    with pytest.raises((TypeError, ValueError)):
        UniverseEligibilityDrainService(client=Client(), checkpoint_writer=lambda value:None,
            clock=lambda:NOW).run(request(1), max_total_items=value)

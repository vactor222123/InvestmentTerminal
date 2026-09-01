from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.models.candle import Candle
from investment_terminal.operations.eligibility_success_projection import EligibilitySuccessProjectionService
from investment_terminal.operations.universe_eligibility_scan import EligibilityScanRequest, UniverseEligibilityScanService


NOW = datetime(2026, 8, 29, tzinfo=timezone.utc)


def request():
    value = {"schema_version": 1, "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity":"NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256":{"NASDAQ_LISTED":"a"*64,"OTHER_LISTED":"b"*64},
        "members":[{"source":"NASDAQ_LISTED","source_symbol":symbol,
            "yahoo_symbol":symbol,"security_name":symbol,"listing_code":"Q","is_etf":False}
            for symbol in ("AAA","BBB","CCC")]}
    return EligibilityScanRequest.from_universe(value, requested_end=NOW)


class Client:
    def get_candles(self,*,symbol,resolution,currency,**kwargs):
        if symbol=="BBB": raise ValueError("private")
        return [Candle(symbol=symbol,resolution=resolution,timestamp=NOW-timedelta(days=1),
            open_price=1,high_price=1,low_price=1,close_price=1,volume=1,currency=currency)]


def complete_checkpoint(req):
    writes=[]
    UniverseEligibilityScanService(client=Client(),checkpoint_writer=writes.append,
        clock=lambda:NOW).run(req,max_items=3)
    return writes[-1]


def test_projects_only_successes_and_redacts_report():
    req=request()
    private,report=EligibilitySuccessProjectionService(clock=lambda:NOW).run(
        req,complete_checkpoint(req))
    assert [x["yahoo_symbol"] for x in private["members"]]==["AAA","CCC"]
    assert report["coverage"]=={"member_count":3,"success_count":2,"excluded_count":1}
    assert report["projection_checksum"] and "AAA" not in str(report)


def test_incomplete_checkpoint_fails_closed():
    req=request(); checkpoint=complete_checkpoint(req)
    checkpoint["outcomes"].pop("NASDAQ_LISTED:CCC")
    with pytest.raises(ValueError,match="not complete"):
        EligibilitySuccessProjectionService(clock=lambda:NOW).run(req,checkpoint)


def test_mismatched_checkpoint_fails_closed():
    req=request(); checkpoint=complete_checkpoint(req); checkpoint["request_checksum"]="0"*64
    with pytest.raises(ValueError,match="does not match"):
        EligibilitySuccessProjectionService(clock=lambda:NOW).run(req,checkpoint)

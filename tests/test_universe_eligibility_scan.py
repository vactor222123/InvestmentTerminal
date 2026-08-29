from datetime import datetime, timedelta, timezone

import pytest
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError

from investment_terminal.models.candle import Candle
from investment_terminal.operations.universe_eligibility_scan import (
    EligibilityScanRequest,
    UniverseEligibilityScanService,
)
from investment_terminal.utils.exceptions import APIError


END = datetime(2026, 8, 29, tzinfo=timezone.utc)


def universe(count=3, *, missing=False):
    return {"schema_version": 1, "universe_identity": "BROAD_US_LISTED_SECURITIES",
        "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
        "archive_sha256": {"NASDAQ_LISTED": "a"*64, "OTHER_LISTED": "b"*64},
        "members": [{"source": "NASDAQ_LISTED", "source_symbol": f"S{i:03d}",
            "yahoo_symbol": None if missing and i == 0 else f"S{i:03d}",
            "security_name": f"Security {i}", "listing_code": "Q", "is_etf": False}
            for i in range(count)]}


def request(count=3, *, missing=False):
    return EligibilityScanRequest.from_universe(universe(count, missing=missing), requested_end=END)


def candle(symbol):
    return Candle(symbol=symbol, resolution="D", timestamp=END-timedelta(days=1),
        open_price=5, high_price=5, low_price=5, close_price=5, volume=10, currency="USD")


def wrapped(cause):
    try: raise cause
    except Exception as exc: raise APIError("redacted") from exc


class Client:
    def __init__(self, outcomes=None): self.outcomes=outcomes or {}; self.calls=[]
    def get_candles(self, *, symbol, **kwargs):
        self.calls.append(symbol); outcome=self.outcomes.get(symbol,[candle(symbol)])
        if isinstance(outcome, BaseException): raise outcome
        if callable(outcome): return outcome()
        return outcome


def v1_outcome(symbol, status, *, failure_type=None):
    success = status == "SUCCESS"; empty = status == "EMPTY"
    return {"source":"NASDAQ_LISTED","source_symbol":symbol,"yahoo_symbol":symbol,
        "status":status,"provider_instrument_type":None,
        "observed_start":(END-timedelta(days=1)).isoformat() if success else None,
        "observed_end":(END-timedelta(days=1)).isoformat() if success else None,
        "candle_count":1 if success else (0 if empty else None),
        "positive_volume_day_count":1 if success else (0 if empty else None),
        "median_daily_traded_value":50.0 if success else None,
        "measured_at":END.isoformat(),"failure_type":failure_type}


def checkpoint_v1(req, outcomes):
    return {"schema_version":1,"request_checksum":req.checksum,
        "universe_checksum":req.universe_checksum,"requested_start":req.requested_start.isoformat(),
        "requested_end":req.requested_end.isoformat(),"outcomes":outcomes}


def test_request_keeps_fixed_90_day_checksum_contract():
    value=request(); assert value.requested_start == END-timedelta(days=90)
    assert value.checksum == EligibilityScanRequest.from_universe(
        dict(reversed(list(universe().items()))), requested_end=END).checksum


def test_schema1_migration_is_written_before_provider_call_and_preserves_successes():
    req=request(100); outcomes={}
    for i in range(100):
        symbol=f"S{i:03d}"
        outcomes[f"NASDAQ_LISTED:{symbol}"]=v1_outcome(
            symbol,"SUCCESS" if i<10 else "FAILED",failure_type=None if i<10 else "APIError")
    writes=[]; client=Client({"S010": []})
    report=UniverseEligibilityScanService(client=client,checkpoint_writer=writes.append,
        clock=lambda:END).run(req,checkpoint_v1(req,outcomes),max_items=1)
    assert writes[0]["schema_version"] == 3
    assert writes[0]["outcomes"]["NASDAQ_LISTED:S000"]["status"] == "SUCCESS"
    assert sum(x["status"]=="RETRY_PENDING" for x in writes[0]["outcomes"].values()) == 90
    assert client.calls == ["S010"]
    assert report["coverage"]["current_run"] == {"attempted_count":1,
        "provider_request_count":1,"migrated_outcome_count":100}
    assert report["coverage"]["cumulative"]["success_count"] == 10


def test_retry_pending_precedes_new_members_and_success_is_terminal():
    req=request(3); old={"NASDAQ_LISTED:S000":v1_outcome("S000","SUCCESS"),
        "NASDAQ_LISTED:S002":v1_outcome("S002","FAILED",failure_type="APIError")}
    client=Client(); writes=[]
    report=UniverseEligibilityScanService(client=client,checkpoint_writer=writes.append,
        clock=lambda:END).run(req,checkpoint_v1(req,old),max_items=2)
    assert client.calls == ["S002","S001"]
    assert report["status"] == "COMPLETE"
    assert report["coverage"]["cumulative"]["success_count"] == 3


def test_rate_limit_is_checkpointed_retryable_and_halts_immediately():
    req=request(3)
    def rate_limit(): wrapped(YFRateLimitError())
    client=Client({"S000":rate_limit}); writes=[]
    report=UniverseEligibilityScanService(client=client,checkpoint_writer=writes.append,
        clock=lambda:END).run(req,max_items=3)
    assert client.calls == ["S000"]
    assert writes[-1]["outcomes"]["NASDAQ_LISTED:S000"]["status"] == "RETRY_PENDING"
    assert report["status"] == "PAUSED" and report["halt_category"] == "RATE_LIMITED"
    assert report["failure_categories"] == {"RATE_LIMITED":1}


def test_no_price_data_is_final_and_does_not_block_next_member():
    req=request(2)
    def missing(): wrapped(YFPricesMissingError("PRIVATE",""))
    client=Client({"S000":missing}); writes=[]
    report=UniverseEligibilityScanService(client=client,checkpoint_writer=writes.append,
        clock=lambda:END).run(req,max_items=2)
    assert client.calls == ["S000","S001"]
    assert report["coverage"]["cumulative"]["final_failure_count"] == 1
    assert report["failure_categories"] == {"NO_PRICE_DATA":1}


def test_retry_reaches_final_failure_on_third_attempt():
    req=request(1); first=v1_outcome("S000","FAILED",failure_type="TimeoutError")
    writes=[]; client=Client({"S000":TimeoutError("private")})
    service=UniverseEligibilityScanService(client=client,checkpoint_writer=writes.append,clock=lambda:END)
    second=service.run(req,checkpoint_v1(req,{"NASDAQ_LISTED:S000":first}),max_items=1)
    assert second["coverage"]["cumulative"]["retry_pending_count"] == 1
    third=service.run(req,writes[-1],max_items=1)
    assert third["status"] == "COMPLETE"
    assert third["coverage"]["cumulative"]["final_failure_count"] == 1
    assert writes[-1]["outcomes"]["NASDAQ_LISTED:S000"]["attempt_count"] == 3


def test_exact_resume_bypasses_every_terminal_status():
    req=request(3,missing=True); writes=[]; first=Client({"S001":[],"S002":ValueError("bad")})
    report=UniverseEligibilityScanService(client=first,checkpoint_writer=writes.append,
        clock=lambda:END).run(req,max_items=3)
    assert report["status"] == "COMPLETE"
    second=Client()
    repeated=UniverseEligibilityScanService(client=second,
        checkpoint_writer=lambda value:pytest.fail("terminal resume wrote checkpoint"),
        clock=lambda:END).run(req,writes[-1],max_items=3)
    assert second.calls == [] and repeated["coverage"]["current_run"]["attempted_count"] == 0


def test_schema3_report_is_redacted_and_has_no_ranking_output():
    report=UniverseEligibilityScanService(client=Client(),checkpoint_writer=lambda value:None,
        clock=lambda:END).run(request(101),max_items=100)
    assert report["schema_version"] == 3 and report["status"] == "IN_PROGRESS"
    assert report["coverage"]["cumulative"]["never_attempted_count"] == 1
    assert "S000" not in str(report) and "50.0" not in str(report) and "rank" not in report


@pytest.mark.parametrize("field,value",[("request_checksum","0"*64),
    ("universe_checksum","0"*64),("requested_end","2026-01-01T00:00:00+00:00")])
def test_mismatched_checkpoint_fails_closed(field,value):
    req=request(1); payload=checkpoint_v1(req,{}) ; payload[field]=value
    with pytest.raises(ValueError,match="does not match"):
        UniverseEligibilityScanService(client=Client(),checkpoint_writer=lambda value:None,
            clock=lambda:END).run(req,payload)


def test_corrupt_schema2_retry_outcome_fails_closed():
    req=request(1); value={**v1_outcome("S000","FAILED",failure_type="APIError"),
        "status":"RETRY_PENDING","attempt_count":3,"failure_category":"RATE_LIMITED"}
    value.pop("failure_type")
    payload={**checkpoint_v1(req,{"NASDAQ_LISTED:S000":value}),"schema_version":2}
    with pytest.raises(ValueError,match="Retry-pending"):
        UniverseEligibilityScanService(client=Client(),checkpoint_writer=lambda value:None,
            clock=lambda:END).run(req,payload)


def test_schema2_invalid_responses_migrate_before_one_final_retry():
    req = request(100)
    outcomes = {}
    for i in range(100):
        symbol = f"S{i:03d}"
        if i < 10:
            item = {**v1_outcome(symbol, "SUCCESS"), "attempt_count": 1,
                    "failure_category": None}
            item.pop("failure_type")
        else:
            category = "NO_PRICE_DATA" if i < 12 else "INVALID_RESPONSE"
            item = {**v1_outcome(symbol, "FAILED"), "status": "FINAL_FAILED",
                    "attempt_count": 2, "failure_category": category}
            item.pop("failure_type")
        outcomes[f"NASDAQ_LISTED:{symbol}"] = item
    checkpoint = {**checkpoint_v1(req, outcomes), "schema_version": 2}
    writes = []
    service = UniverseEligibilityScanService(
        client=Client({"S012": []}), checkpoint_writer=writes.append,
        clock=lambda: END,
    )

    report = service.run(req, checkpoint, max_items=1)

    migrated = writes[0]["outcomes"]
    assert writes[0]["schema_version"] == 3
    assert sum(item["status"] == "RETRY_PENDING" for item in migrated.values()) == 88
    assert migrated["NASDAQ_LISTED:S010"]["failure_category"] == "NO_PRICE_DATA"
    assert migrated["NASDAQ_LISTED:S012"]["attempt_count"] == 2
    assert report["coverage"]["current_run"]["migrated_outcome_count"] == 100
    assert writes[-1]["outcomes"]["NASDAQ_LISTED:S012"]["attempt_count"] == 3


@pytest.mark.parametrize("maximum",[0,101,True,1.5])
def test_slice_bound_is_validated(maximum):
    with pytest.raises((TypeError,ValueError)):
        UniverseEligibilityScanService(client=Client(),checkpoint_writer=lambda value:None,
            clock=lambda:END).run(request(1),max_items=maximum)

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from investment_terminal.operations.resumable_market_batch import MarketBatchRequest, ResumableMarketBatchService

NOW=datetime(2026,8,27,tzinfo=timezone.utc)

@dataclass
class Result:
    downloaded:int=2;inserted:int=2;duplicates:int=0

class Importer:
    def __init__(self,fail=()):self.fail=set(fail);self.calls=[]
    def import_candles(self,**kw):
        self.calls.append(kw["symbol"])
        if kw["symbol"] in self.fail:raise TimeoutError()
        return Result()

def request():
    return MarketBatchRequest.from_dict({"schema_version":1,"resolution":"D",
        "start":"2016-08-27T00:00:00Z","end":"2026-08-27T00:00:00Z",
        "items":[{"symbol":"BBB","currency":"USD"},{"symbol":"AAA","currency":"USD"}]})

def test_isolates_failure_and_checkpoints_each_item():
    importer=Importer(("AAA",));written=[]
    report=ResumableMarketBatchService(importer=importer,checkpoint_writer=written.append,clock=lambda:NOW).run(request())
    assert importer.calls==["AAA","BBB"]
    assert report["status"]=="PARTIAL"
    assert report["schema_version"]==3
    assert report["coverage"]["current_run"]=={"attempted_count":2,"skipped_count":0,
        "downloaded_total":2,"inserted_total":2,"duplicate_total":0,
        "omitted_trailing_total":0,"omission_types":[]}
    assert report["coverage"]["cumulative"]["failure_count"]==1
    assert len(written)==2 and "AAA" not in str(report) and report["failure_types"]==["TimeoutError"]

def test_resume_skips_success_and_retries_failure():
    req=request();importer=Importer();written=[]
    checkpoint={"schema_version":1,"request_checksum":req.checksum,"outcomes":{
        "AAA":{"status":"FAILED","downloaded":None,"inserted":None,"duplicates":None,"failure_type":"TimeoutError"},
        "BBB":{"status":"SUCCESS","downloaded":2,"inserted":2,"duplicates":0,"failure_type":None}}}
    report=ResumableMarketBatchService(importer=importer,checkpoint_writer=written.append,clock=lambda:NOW).run(req,checkpoint)
    assert importer.calls==["AAA"] and report["status"]=="SUCCESS"
    assert report["coverage"]["current_run"]=={"attempted_count":1,"skipped_count":1,
        "downloaded_total":2,"inserted_total":2,"duplicate_total":0,
        "omitted_trailing_total":0,"omission_types":[]}

def test_exact_resume_reports_zero_current_transfer_totals():
    req=request();importer=Importer()
    outcome={"status":"SUCCESS","downloaded":2,"inserted":2,"duplicates":0,"failure_type":None}
    checkpoint={"schema_version":1,"request_checksum":req.checksum,"outcomes":{"AAA":outcome,"BBB":outcome}}
    report=ResumableMarketBatchService(importer=importer,checkpoint_writer=lambda x:None,clock=lambda:NOW).run(req,checkpoint)
    assert importer.calls==[]
    assert report["coverage"]["current_run"]=={"attempted_count":0,"skipped_count":2,
        "downloaded_total":0,"inserted_total":0,"duplicate_total":0,
        "omitted_trailing_total":0,"omission_types":[]}
    assert report["coverage"]["cumulative"]["downloaded_total"]==4

def test_schema2_checkpoint_persists_and_replays_omission_evidence():
    req=request();written=[]
    importer=Importer()
    importer.import_candles=lambda **kw: type("Result",(),{"downloaded":1,"inserted":1,
        "duplicates":0,"omitted_trailing_count":1,
        "omission_types":("TRAILING_NON_FINITE_NUMERIC",)})()
    report=ResumableMarketBatchService(importer=importer,checkpoint_writer=written.append,clock=lambda:NOW).run(req)
    assert written[-1]["schema_version"]==2
    assert report["coverage"]["cumulative"]["omitted_trailing_total"]==2
    assert report["coverage"]["cumulative"]["omission_types"]==["TRAILING_NON_FINITE_NUMERIC"]
    replay=ResumableMarketBatchService(importer=Importer(),checkpoint_writer=lambda x:None,clock=lambda:NOW).run(req,written[-1])
    assert replay["coverage"]["current_run"]["attempted_count"]==0
    assert replay["coverage"]["cumulative"]["omitted_trailing_total"]==2

def test_rejects_inconsistent_schema2_omission_before_resume():
    req=request();outcome={"status":"SUCCESS","downloaded":1,"inserted":1,"duplicates":0,
        "omitted_trailing_count":1,"omission_types":[],"failure_type":None}
    checkpoint={"schema_version":2,"request_checksum":req.checksum,"outcomes":{"AAA":outcome,"BBB":outcome}}
    with pytest.raises(ValueError,match="omission"):
        ResumableMarketBatchService(importer=Importer(),checkpoint_writer=lambda x:None,clock=lambda:NOW).run(req,checkpoint)

def test_rejects_mismatched_checkpoint_before_import():
    importer=Importer()
    with pytest.raises(ValueError,match="does not match"):
        ResumableMarketBatchService(importer=importer,checkpoint_writer=lambda x:None,clock=lambda:NOW).run(
            request(),{"schema_version":1,"request_checksum":"bad","outcomes":{}})
    assert importer.calls==[]

@pytest.mark.parametrize("items",[[],[{"symbol":"A","currency":"USD"}]*2,[{"symbol":str(i),"currency":"USD"} for i in range(21)]])
def test_request_bounds_and_uniqueness(items):
    with pytest.raises(ValueError):
        MarketBatchRequest.from_dict({"schema_version":1,"resolution":"D","start":"2016-01-01T00:00:00Z",
                                      "end":"2026-01-01T00:00:00Z","items":items})

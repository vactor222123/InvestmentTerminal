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
    assert report["schema_version"]==2
    assert report["coverage"]["current_run"]=={"attempted_count":2,"skipped_count":0,
        "downloaded_total":2,"inserted_total":2,"duplicate_total":0}
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
        "downloaded_total":2,"inserted_total":2,"duplicate_total":0}

def test_exact_resume_reports_zero_current_transfer_totals():
    req=request();importer=Importer()
    outcome={"status":"SUCCESS","downloaded":2,"inserted":2,"duplicates":0,"failure_type":None}
    checkpoint={"schema_version":1,"request_checksum":req.checksum,"outcomes":{"AAA":outcome,"BBB":outcome}}
    report=ResumableMarketBatchService(importer=importer,checkpoint_writer=lambda x:None,clock=lambda:NOW).run(req,checkpoint)
    assert importer.calls==[]
    assert report["coverage"]["current_run"]=={"attempted_count":0,"skipped_count":2,
        "downloaded_total":0,"inserted_total":0,"duplicate_total":0}
    assert report["coverage"]["cumulative"]["downloaded_total"]==4

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

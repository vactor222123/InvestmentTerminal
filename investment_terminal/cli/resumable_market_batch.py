"""CLI for bounded resumable Yahoo market-data ingestion."""
import argparse, json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.resumable_market_batch import MarketBatchRequest, ResumableMarketBatchService
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.services.historical_market_service import HistoricalMarketService
from investment_terminal.utils.atomic_write import write_json_atomic

def parser():
    p=argparse.ArgumentParser(description="Run one bounded resumable market batch.")
    p.add_argument("--request",type=Path,required=True);p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--database",type=Path,required=True);p.add_argument("--cache-directory",type=Path,required=True)
    p.add_argument("--report-output",type=Path,required=True);p.add_argument("--json",action="store_true");return p

def main(argv: Sequence[str]|None=None, *, client=None, clock=None):
    o=parser().parse_args(argv);db=None;runtime_clock=clock or (lambda:datetime.now(timezone.utc))
    try:
        request=MarketBatchRequest.from_dict(json.loads(o.request.read_text(encoding="utf-8")))
        checkpoint=json.loads(o.checkpoint.read_text(encoding="utf-8")) if o.checkpoint.exists() else None
        db=Database(o.database);db.initialize()
        importer=HistoricalMarketService(client or YahooFinanceClient(cache_directory=o.cache_directory),CandleRepository(db))
        payload=ResumableMarketBatchService(importer=importer,checkpoint_writer=lambda x:write_json_atomic(o.checkpoint,x),clock=runtime_clock).run(request,checkpoint)
    except Exception as exc:
        now=runtime_clock();payload={"schema_version":1,"provider_identity":"YAHOO_FINANCE","status":"FAILED",
            "started_at":now.isoformat(),"completed_at":now.isoformat(),"duration_seconds":0.0,"coverage":None,
            "failure_types":[type(exc).__name__],"limitations":["failed batch report excludes private values and exception messages"]}
    finally:
        if db is not None: db.close()
    write_json_atomic(o.report_output,payload)
    if o.json: print(json.dumps(payload,indent=2,allow_nan=False))
    return 0 if payload["status"]=="SUCCESS" else 1

if __name__=="__main__": raise SystemExit(main())

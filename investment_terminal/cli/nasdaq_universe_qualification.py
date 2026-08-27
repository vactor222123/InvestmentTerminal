"""CLI for official Nasdaq Trader universe qualification."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from investment_terminal.clients.nasdaq_symbol_directory_client import NasdaqSymbolDirectoryClient
from investment_terminal.operations.nasdaq_universe_qualification import NasdaqUniverseQualificationService
from investment_terminal.utils.atomic_write import write_json_atomic
def main(argv=None,*,client=None,clock=None):
    p=argparse.ArgumentParser();p.add_argument("--archive-directory",type=Path,required=True);p.add_argument("--private-universe-output",type=Path,required=True);p.add_argument("--report-output",type=Path,required=True);p.add_argument("--timeout-seconds",type=float,default=30);p.add_argument("--json",action="store_true");o=p.parse_args(argv);runtime=clock or(lambda:datetime.now(timezone.utc))
    try:
        private,report=NasdaqUniverseQualificationService(client=client or NasdaqSymbolDirectoryClient(timeout_seconds=o.timeout_seconds),archive_directory=o.archive_directory,clock=runtime).qualify();write_json_atomic(o.private_universe_output,private)
    except Exception as exc:
        now=runtime();report={"schema_version":1,"universe_identity":"BROAD_US_LISTED_SECURITIES","source_identity":"NASDAQ_TRADER_SYMBOL_DIRECTORY","status":"FAILED","started_at":now.isoformat(),"completed_at":now.isoformat(),"duration_seconds":0.0,"coverage":None,"file_creation_times":None,"archive_sha256":None,"failure":{"type":type(exc).__name__,"reason":"Nasdaq universe qualification failed"},"limitations":["failed report excludes private values and exception messages"]}
    write_json_atomic(o.report_output,report)
    if o.json:print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["status"]=="SUCCESS" else 1
if __name__=="__main__":raise SystemExit(main())

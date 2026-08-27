"""Qualification of official Nasdaq Trader broad-US symbol directories."""
import csv,io,re
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from investment_terminal.utils.validation import validate_aware_datetime

class NasdaqUniverseQualificationService:
    REQUIRED={"NASDAQ_LISTED":("Symbol","Security Name","Market Category","Test Issue","Financial Status","ETF"),
              "OTHER_LISTED":("ACT Symbol","Security Name","Exchange","ETF","Test Issue")}
    def __init__(self,*,client,archive_directory:Path,clock,minimum_accepted:int=1000):
        self.client=client;self.archive_directory=Path(archive_directory);self.clock=clock
        if minimum_accepted<1:raise ValueError("minimum_accepted must be positive")
        self.minimum_accepted=minimum_accepted
    def qualify(self):
        started=validate_aware_datetime(self.clock(),field_name="started_at")
        raw=self.client.fetch();parsed=[];checksums={};creation={};counts={"source_rows":0,"accepted":0,"etf":0,"non_etf":0,"excluded_test":0,"excluded_status":0,"projection_failure":0}
        for source in ("NASDAQ_LISTED","OTHER_LISTED"):
            data=raw[source];digest=sha256(data).hexdigest();checksums[source]=digest;self._archive(source,digest,data)
            rows,created=self._parse(source,data);creation[source]=created.isoformat();counts["source_rows"]+=len(rows)
            for row in rows:
                if row["Test Issue"]=="Y":counts["excluded_test"]+=1;continue
                if source=="NASDAQ_LISTED" and row["Financial Status"] not in ("N",""):counts["excluded_status"]+=1;continue
                source_symbol=row["Symbol"] if source=="NASDAQ_LISTED" else row["ACT Symbol"]
                yahoo=self._project(source_symbol)
                if yahoo is None:counts["projection_failure"]+=1;continue
                etf=row["ETF"]=="Y";counts["etf" if etf else "non_etf"]+=1;counts["accepted"]+=1
                parsed.append({"source":source,"source_symbol":source_symbol,"yahoo_symbol":yahoo,"security_name":row["Security Name"],
                    "listing_code":row["Market Category"] if source=="NASDAQ_LISTED" else row["Exchange"],"is_etf":etf})
        parsed.sort(key=lambda x:(x["yahoo_symbol"],x["source"]))
        symbols=[x["yahoo_symbol"] for x in parsed]
        collisions=len(symbols)-len(set(symbols))
        if collisions:raise ValueError("Normalized universe contains symbol collisions")
        if len(parsed)<self.minimum_accepted:raise ValueError("Accepted universe is below qualification minimum")
        completed=validate_aware_datetime(self.clock(),field_name="completed_at")
        private={"schema_version":1,"universe_identity":"BROAD_US_LISTED_SECURITIES","source_identity":"NASDAQ_TRADER_SYMBOL_DIRECTORY",
            "retrieved_at":completed.isoformat(),"file_creation_times":creation,"archive_sha256":checksums,"members":parsed}
        report={"schema_version":1,"universe_identity":"BROAD_US_LISTED_SECURITIES","source_identity":"NASDAQ_TRADER_SYMBOL_DIRECTORY",
            "status":"SUCCESS","started_at":started.isoformat(),"completed_at":completed.isoformat(),"duration_seconds":(completed-started).total_seconds(),
            "coverage":{**counts,"source_file_count":2,"unique_yahoo_symbol_count":len(set(symbols)),"collision_count":collisions},
            "file_creation_times":creation,"archive_sha256":checksums,"failure":None,
            "limitations":["report excludes member symbols, names, paths, provider bodies, and exception messages","qualification does not generate candle requests or authorize ingestion"]}
        return private,report
    def _archive(self,source,digest,data):
        self.archive_directory.mkdir(parents=True,exist_ok=True);path=self.archive_directory/f"{source.lower()}.{digest}.txt"
        try:
            with path.open("xb") as handle:handle.write(data)
        except FileExistsError:
            if path.read_bytes()!=data:raise RuntimeError("Existing archive content mismatch")
    @classmethod
    def _parse(cls,source,data):
        try:text=data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:raise ValueError("Directory file is not UTF-8") from exc
        lines=text.splitlines()
        if len(lines)<3:raise ValueError("Directory file is truncated")
        reader=csv.DictReader(lines[:-1],delimiter="|")
        if reader.fieldnames is None or any(x not in reader.fieldnames for x in cls.REQUIRED[source]):raise ValueError("Directory headers are invalid")
        tail=lines[-1].split("|",1)[0]
        if not tail.startswith("File Creation Time: "):raise ValueError("Directory creation time is missing")
        try:created=datetime.strptime(tail.removeprefix("File Creation Time: "),"%m%d%Y%H:%M").replace(tzinfo=ZoneInfo("America/New_York"))
        except ValueError as exc:raise ValueError("Directory creation time is invalid") from exc
        rows=[]
        for row in reader:
            normalized={k:(v or "").strip() for k,v in row.items() if k is not None}
            if any(not normalized[x] for x in cls.REQUIRED[source]):raise ValueError("Directory row is missing required fields")
            if normalized["Test Issue"] not in {"Y","N"} or normalized["ETF"] not in {"Y","N"}:raise ValueError("Directory flags are invalid")
            rows.append(normalized)
        return rows,created
    @staticmethod
    def _project(value):
        value=value.strip().upper().replace(".","-")
        return value if re.fullmatch(r"[A-Z0-9-]+",value) else None

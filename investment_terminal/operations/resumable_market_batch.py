"""Sequential resumable ingestion for one bounded market-data batch."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


@dataclass(frozen=True, slots=True, order=True)
class MarketBatchItem:
    symbol: str
    currency: str


@dataclass(frozen=True, slots=True)
class MarketBatchRequest:
    resolution: str
    start: datetime
    end: datetime
    items: tuple[MarketBatchItem, ...]

    @classmethod
    def from_dict(cls, value: object) -> "MarketBatchRequest":
        if not isinstance(value, dict) or value.get("schema_version") != 1:
            raise ValueError("Unsupported market batch request schema")
        resolution = normalize_required_text(value.get("resolution"), field_name="resolution", uppercase=True)
        if resolution not in {"D", "W", "M"}:
            raise ValueError("Unsupported resolution")
        start = _datetime(value.get("start"), "start")
        end = _datetime(value.get("end"), "end")
        if start >= end:
            raise ValueError("start must be earlier than end")
        rows = value.get("items")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 20 or any(not isinstance(row, dict) for row in rows):
            raise ValueError("items must contain between 1 and 20 objects")
        items = tuple(sorted(MarketBatchItem(
            normalize_required_text(row.get("symbol"), field_name="symbol", uppercase=True),
            normalize_required_text(row.get("currency"), field_name="currency", uppercase=True),
        ) for row in rows))
        if len({item.symbol for item in items}) != len(items):
            raise ValueError("items must contain unique symbols")
        return cls(resolution, start, end, items)

    def canonical_dict(self) -> dict[str, object]:
        return {"schema_version": 1, "resolution": self.resolution,
                "start": self.start.isoformat(), "end": self.end.isoformat(),
                "items": [{"symbol": x.symbol, "currency": x.currency} for x in self.items]}

    @property
    def checksum(self) -> str:
        raw = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(raw.encode("utf-8")).hexdigest()


class ResumableMarketBatchService:
    def __init__(self, *, importer, checkpoint_writer, clock) -> None:
        self.importer = importer
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(self, request: MarketBatchRequest, checkpoint: object | None = None) -> dict[str, object]:
        if not isinstance(request, MarketBatchRequest):
            raise TypeError("request must be a MarketBatchRequest")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        outcomes = self._outcomes(checkpoint, request.checksum)
        skipped = 0
        current_outcomes: list[dict[str, object]] = []
        for item in request.items:
            previous = outcomes.get(item.symbol)
            if previous is not None and previous["status"] in {"SUCCESS", "EMPTY"}:
                skipped += 1
                continue
            try:
                result = self.importer.import_candles(
                    symbol=item.symbol, resolution=request.resolution,
                    start=request.start, end=request.end, currency=item.currency)
                status = "SUCCESS" if result.downloaded else "EMPTY"
                outcomes[item.symbol] = {"status": status, "downloaded": result.downloaded,
                    "inserted": result.inserted, "duplicates": result.duplicates,
                    "failure_type": None}
            except Exception as exc:
                outcomes[item.symbol] = {"status": "FAILED", "downloaded": None,
                    "inserted": None, "duplicates": None, "failure_type": type(exc).__name__}
            current_outcomes.append(outcomes[item.symbol])
            self.checkpoint_writer({"schema_version": 1, "request_checksum": request.checksum,
                                    "outcomes": outcomes})
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        values = [outcomes[item.symbol] for item in request.items]
        success = sum(x["status"] == "SUCCESS" for x in values)
        empty = sum(x["status"] == "EMPTY" for x in values)
        failed = sum(x["status"] == "FAILED" for x in values)
        status = "SUCCESS" if failed == 0 else ("PARTIAL" if success + empty else "FAILED")
        return {"schema_version": 2, "provider_identity": "YAHOO_FINANCE", "status": status,
            "started_at": started.isoformat(), "completed_at": completed.isoformat(),
            "duration_seconds": (completed-started).total_seconds(), "coverage": {
                "current_run": {"attempted_count": len(current_outcomes), "skipped_count": skipped,
                    "downloaded_total": sum(x["downloaded"] or 0 for x in current_outcomes),
                    "inserted_total": sum(x["inserted"] or 0 for x in current_outcomes),
                    "duplicate_total": sum(x["duplicates"] or 0 for x in current_outcomes)},
                "cumulative": {"requested_count": len(request.items), "success_count": success,
                    "empty_count": empty, "failure_count": failed,
                    "downloaded_total": sum(x["downloaded"] or 0 for x in values),
                    "inserted_total": sum(x["inserted"] or 0 for x in values),
                    "duplicate_total": sum(x["duplicates"] or 0 for x in values)}},
            "failure_types": sorted({x["failure_type"] for x in values if x["failure_type"]}),
            "limitations": ["report excludes symbols, paths, prices, provider text, and exception messages",
                            "batch execution does not authorize scheduling, mass ingestion, analysis, or trading"]}

    @staticmethod
    def _outcomes(value: object | None, checksum: str) -> dict[str, dict[str, object]]:
        if value is None:
            return {}
        if not isinstance(value, dict) or value.get("schema_version") != 1 or value.get("request_checksum") != checksum:
            raise ValueError("Checkpoint does not match request")
        outcomes = value.get("outcomes")
        if not isinstance(outcomes, dict) or any(not isinstance(k, str) or not isinstance(v, dict) for k, v in outcomes.items()):
            raise ValueError("Checkpoint outcomes are invalid")
        return dict(outcomes)


def _datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    return validate_aware_datetime(parsed, field_name=field_name)

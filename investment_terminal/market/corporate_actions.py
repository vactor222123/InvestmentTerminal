"""Immutable normalized action observations, never broker cash transactions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
import re
from zoneinfo import ZoneInfo

from investment_terminal.utils.validation import (
    validate_aware_datetime,
    validate_finite_number,
)


ACTION_KINDS = ("CAPITAL_GAIN", "DIVIDEND", "SPLIT")
MAX_ROWS = 4000
LIMITATIONS = (
    "yfinance normalized observations; raw field presence and completeness unknown",
    "zero events does not prove that no corporate actions occurred",
    "cash action currency and historical per-share adjustment basis unverified",
    "quote currency is not evidence of dividend settlement currency",
    "no candle adjustment, total return, broker payment or portfolio mutation",
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _utc(value: datetime) -> datetime:
    value = validate_aware_datetime(value, field_name="timestamp")
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return value


@dataclass(frozen=True, slots=True)
class CorporateAction:
    timestamp: datetime
    session_date: str
    kind: str
    value: float

    def __post_init__(self):
        _utc(self.timestamp)
        if self.kind not in ACTION_KINDS:
            raise ValueError("Unsupported action kind")
        value = validate_finite_number(self.value, field_name="action value")
        if value <= 0 or (self.kind == "SPLIT" and value == 1):
            raise ValueError("Invalid action value")
        object.__setattr__(self, "value", value)

    def to_dict(self):
        return {
            "timestamp_utc": self.timestamp.isoformat(),
            "session_date": self.session_date,
            "kind": self.kind,
            "value": self.value,
            "unit": ("NEW_SHARES_PER_OLD_SHARE" if self.kind == "SPLIT"
                     else "NORMALIZED_AMOUNT_PER_SHARE"),
            "currency": None,
        }


@dataclass(frozen=True, slots=True)
class CorporateActionSnapshot:
    symbol: str
    start: datetime
    end: datetime
    fetched_at: datetime
    adapter_version: str
    quote_currency: str
    exchange_timezone: str
    instrument_type: str
    row_count: int
    first_row_at: datetime
    last_row_at: datetime
    capital_gains_present: bool
    events: tuple[CorporateAction, ...]

    def __post_init__(self):
        if (not isinstance(self.symbol, str)
                or re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=_-]{0,63}", self.symbol) is None):
            raise ValueError("Invalid provider symbol")
        for value in (self.start, self.end, self.fetched_at,
                      self.first_row_at, self.last_row_at):
            _utc(value)
        if (self.start.time() != datetime.min.time()
                or self.end.time() != datetime.min.time()
                or not self.start < self.end <= self.start + timedelta(days=3660)
                or self.end > self.fetched_at
                or not self.start <= self.first_row_at <= self.last_row_at < self.end):
            raise ValueError("Invalid snapshot window")
        if (not isinstance(self.adapter_version, str)
                or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.adapter_version) is None):
            raise ValueError("Invalid adapter version")
        # Preserve case: GBp and GBP are not interchangeable units.
        if (not isinstance(self.quote_currency, str)
                or re.fullmatch(r"[A-Za-z]{3}", self.quote_currency) is None):
            raise ValueError("Invalid quote currency")
        if self.instrument_type not in ("EQUITY", "ETF", "MUTUALFUND"):
            raise ValueError("Unsupported instrument type")
        zone = ZoneInfo(self.exchange_timezone)
        if type(self.row_count) is not int or not 1 <= self.row_count <= MAX_ROWS:
            raise ValueError("Invalid row count")
        if type(self.capital_gains_present) is not bool:
            raise ValueError("Invalid field availability")
        if not isinstance(self.events, tuple) or len(self.events) > self.row_count * 3:
            raise ValueError("Invalid events")
        previous = None
        for event in self.events:
            if not isinstance(event, CorporateAction):
                raise ValueError("Invalid event type")
            key = (event.timestamp, event.kind)
            if (not self.first_row_at <= event.timestamp <= self.last_row_at
                    or previous is not None and key <= previous
                    or event.session_date != event.timestamp.astimezone(zone).date().isoformat()
                    or event.kind == "CAPITAL_GAIN" and not self.capital_gains_present):
                raise ValueError("Invalid event identity, order or date")
            previous = key

    def content(self):
        return {
            "symbol": self.symbol,
            "start_utc": self.start.isoformat(),
            "end_utc_exclusive": self.end.isoformat(),
            "adapter_version": self.adapter_version,
            "quote_currency": self.quote_currency,
            "exchange_timezone": self.exchange_timezone,
            "instrument_type": self.instrument_type,
            "request_flags": {"interval": "1d", "actions": True,
                              "auto_adjust": False, "back_adjust": False,
                              "repair": False, "keepna": True, "rounding": False},
            "row_count": self.row_count,
            "first_row_at": self.first_row_at.isoformat(),
            "last_row_at": self.last_row_at.isoformat(),
            "capital_gains_present": self.capital_gains_present,
            "events": [event.to_dict() for event in self.events],
        }

    def to_dict(self):
        content = self.content()
        return {
            "schema_version": 1,
            "operation_identity": "YAHOO_CORPORATE_ACTION_SNAPSHOT",
            "provider_identity": "YAHOO_FINANCE",
            "observed_layer": "YFINANCE_HISTORY_FRAME",
            "fetched_at_utc": self.fetched_at.isoformat(),
            "raw_source_presence": "UNKNOWN",
            "action_completeness": "UNKNOWN",
            "content": content,
            "content_sha256": sha256(canonical_bytes(content)).hexdigest(),
            "limitations": list(LIMITATIONS),
        }

    @classmethod
    def from_dict(cls, payload):
        """Revalidate persisted data, including exact schema, units and checksum."""
        try:
            content = payload["content"]
            result = cls(
                symbol=content["symbol"],
                start=datetime.fromisoformat(content["start_utc"]),
                end=datetime.fromisoformat(content["end_utc_exclusive"]),
                fetched_at=datetime.fromisoformat(payload["fetched_at_utc"]),
                adapter_version=content["adapter_version"],
                quote_currency=content["quote_currency"],
                exchange_timezone=content["exchange_timezone"],
                instrument_type=content["instrument_type"],
                row_count=content["row_count"],
                first_row_at=datetime.fromisoformat(content["first_row_at"]),
                last_row_at=datetime.fromisoformat(content["last_row_at"]),
                capital_gains_present=content["capital_gains_present"],
                events=tuple(CorporateAction(
                    timestamp=datetime.fromisoformat(event["timestamp_utc"]),
                    session_date=event["session_date"], kind=event["kind"],
                    value=event["value"],
                ) for event in content["events"]),
            )
            # Canonical bytes also distinguish bool/int and unknown extra fields.
            if canonical_bytes(result.to_dict()) != canonical_bytes(payload):
                raise ValueError("Snapshot contract mismatch")
            return result
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Invalid corporate-action snapshot") from exc

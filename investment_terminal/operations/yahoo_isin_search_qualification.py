"""Privacy-safe qualification of one bounded Yahoo ISIN search."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class YahooIsinSearchClient(Protocol):
    def search_isin(self, isin: str) -> list[dict[str, object]]: ...


class YahooIsinSearchStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True, order=True)
class YahooIsinSearchCandidate:
    symbol: str
    exchange: str | None
    exchange_display: str | None
    quote_type: str | None
    currency: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "exchange_display": self.exchange_display,
            "quote_type": self.quote_type,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class YahooIsinSearchQualification:
    status: YahooIsinSearchStatus
    started_at: datetime
    completed_at: datetime
    candidates: tuple[YahooIsinSearchCandidate, ...]
    failure_type: str | None = None

    def private_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE_SEARCH",
            "query_kind": "ISIN",
            "searched_at": self.completed_at.isoformat(),
            "candidates": [item.to_dict() for item in self.candidates],
        }

    def report_dict(self) -> dict[str, object]:
        known = self.status is not YahooIsinSearchStatus.FAILED
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE_SEARCH",
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "coverage": {
                "candidate_count": len(self.candidates) if known else None,
                "unique_symbol_count": len({item.symbol for item in self.candidates}) if known else None,
                "unique_exchange_count": len({item.exchange for item in self.candidates if item.exchange}) if known else None,
            },
            "failure": None if self.failure_type is None else {
                "type": self.failure_type,
                "reason": "Yahoo Finance ISIN search qualification failed",
            },
            "limitations": [
                "report excludes paths, ISINs, symbols, exchanges, names, and provider text",
                "private candidates are discovery evidence, not an accepted metadata mapping",
                "qualification does not mutate quotes, metadata, transactions, or valuations",
            ],
        }


class YahooIsinSearchQualificationService:
    def __init__(self, *, client: YahooIsinSearchClient, clock) -> None:
        self.client = client
        self.clock = clock

    def qualify(self, isin: str) -> YahooIsinSearchQualification:
        normalized_isin = normalize_required_text(isin, field_name="isin", uppercase=True)
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        try:
            rows = self.client.search_isin(normalized_isin)
            candidates = self._normalize(rows)
        except Exception as exc:
            completed = validate_aware_datetime(self.clock(), field_name="completed_at")
            return YahooIsinSearchQualification(
                YahooIsinSearchStatus.FAILED, started, completed, (), type(exc).__name__
            )
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        status = YahooIsinSearchStatus.SUCCESS if candidates else YahooIsinSearchStatus.EMPTY
        return YahooIsinSearchQualification(status, started, completed, candidates)

    @staticmethod
    def _normalize(rows: list[dict[str, object]]) -> tuple[YahooIsinSearchCandidate, ...]:
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise TypeError("Yahoo search result must contain objects")
        candidates = set()
        for row in rows:
            symbol = normalize_required_text(row.get("symbol"), field_name="symbol", uppercase=True)
            candidates.add(YahooIsinSearchCandidate(
                symbol=symbol,
                exchange=_optional(row.get("exchange"), uppercase=True),
                exchange_display=_optional(row.get("exchDisp")),
                quote_type=_optional(row.get("quoteType"), uppercase=True),
                currency=_optional(row.get("currency"), uppercase=True),
            ))
        return tuple(sorted(candidates, key=lambda item: (
            item.symbol, item.exchange or "", item.exchange_display or "",
            item.quote_type or "", item.currency or "",
        )))


def _optional(value: object, *, uppercase: bool = False) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    return normalized.upper() if uppercase else normalized

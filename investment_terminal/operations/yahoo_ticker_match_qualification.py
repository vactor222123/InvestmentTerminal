"""Fail-closed qualification of an existing ticker against Yahoo ISIN candidates."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class YahooTickerMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class YahooTickerMatchQualification:
    status: YahooTickerMatchStatus
    started_at: datetime
    completed_at: datetime
    candidate_count: int | None
    exact_match_count: int | None
    private_match: dict[str, object] | None = None
    failure_type: str | None = None

    def report_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "provider_identity": "YAHOO_FINANCE_SEARCH",
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": (self.completed_at - self.started_at).total_seconds(),
            "coverage": {
                "candidate_count": self.candidate_count,
                "exact_ticker_match_count": self.exact_match_count,
            },
            "failure": None if self.failure_type is None else {
                "type": self.failure_type,
                "reason": "Yahoo ticker-match qualification failed",
            },
            "limitations": [
                "report excludes paths, ISINs, tickers, exchanges, names, prices, and provider text",
                "only an exact existing-ticker match against candidates returned for the same ISIN is accepted",
                "qualification does not mutate quotes, metadata, transactions, or valuations",
            ],
        }


class YahooTickerMatchQualificationService:
    def __init__(self, *, clock) -> None:
        self.clock = clock

    def qualify(self, *, instrument_key: object, exchange_ticker: object,
                candidates: object) -> YahooTickerMatchQualification:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        try:
            key = normalize_required_text(instrument_key, field_name="instrument_key", uppercase=True)
            ticker = normalize_required_text(exchange_ticker, field_name="exchange_ticker", uppercase=True)
            if not isinstance(candidates, list) or any(not isinstance(item, dict) for item in candidates):
                raise TypeError("candidates must contain objects")
            normalized = []
            for item in candidates:
                symbol = normalize_required_text(item.get("symbol"), field_name="symbol", uppercase=True)
                normalized.append({**item, "symbol": symbol})
            matches = [item for item in normalized if item["symbol"] == ticker]
            if len(matches) == 1:
                status = YahooTickerMatchStatus.MATCHED
                private_match = {
                    "schema_version": 1,
                    "provider_identity": "YAHOO_FINANCE_SEARCH",
                    "instrument_key": key,
                    "exchange_ticker": ticker,
                    "candidate": matches[0],
                }
            elif matches:
                status = YahooTickerMatchStatus.AMBIGUOUS
                private_match = None
            else:
                status = YahooTickerMatchStatus.NO_MATCH
                private_match = None
            completed = validate_aware_datetime(self.clock(), field_name="completed_at")
            return YahooTickerMatchQualification(
                status, started, completed, len(normalized), len(matches), private_match
            )
        except Exception as exc:
            completed = validate_aware_datetime(self.clock(), field_name="completed_at")
            return YahooTickerMatchQualification(
                YahooTickerMatchStatus.FAILED, started, completed, None, None,
                failure_type=type(exc).__name__,
            )

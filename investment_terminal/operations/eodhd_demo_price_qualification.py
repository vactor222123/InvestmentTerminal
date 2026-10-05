"""Redacted structural qualification of one public EODHD JSON response."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import isfinite
from typing import Any, Protocol
from urllib.error import HTTPError

from investment_terminal.clients.eodhd_demo_price_client import MAX_RESPONSE_BYTES


FIELDS = ("date", "open", "high", "low", "close", "adjusted_close", "volume")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class DemoPriceClient(Protocol):
    def get_daily_bytes(self, *, start: date, end: date) -> bytes: ...


@dataclass(frozen=True, slots=True)
class DemoPriceRequest:
    start: date
    end: date

    def __post_init__(self) -> None:
        if (
            not isinstance(self.start, date)
            or isinstance(self.start, datetime)
            or not isinstance(self.end, date)
            or isinstance(self.end, datetime)
        ):
            raise ValueError("start and end must be calendar dates")
        if not self.start < self.end or self.end - self.start > timedelta(days=3660):
            raise ValueError("window must be positive and at most 3660 days")


class EodhdDemoPriceQualification:
    def __init__(self, client: DemoPriceClient) -> None:
        self._client = client

    def qualify(self, request: DemoPriceRequest) -> dict[str, Any]:
        if not isinstance(request, DemoPriceRequest):
            raise TypeError("request must be DemoPriceRequest")
        report: dict[str, Any] = {
            "schema_version": 1,
            "provider_identity": "EODHD",
            "access_mode": "PUBLIC_DEMO",
            "public_symbol": "VTI.US",
            "observed_layer": "EODHD_JSON_RESPONSE",
            "qualification_scope": "SOURCE_FIELD_SHAPE_ONLY",
            "request": {
                "start_date": request.start.isoformat(),
                "end_date_exclusive": request.end.isoformat(),
                "period": "d",
                "format": "json",
            },
            "status": None,
            "failure_category": None,
            "response_sha256": None,
            "row_count": None,
            "first_date": None,
            "last_date": None,
            "field_presence_count": {field: 0 for field in FIELDS},
            "limitations": [
                "structural field presence does not verify adjustments or actions",
                "one demo ETF does not establish broad coverage or paid entitlement",
                "no source values, adjusted returns, or candles are stored",
            ],
        }
        try:
            body = self._client.get_daily_bytes(start=request.start, end=request.end)
        except HTTPError as exc:
            return self._failed(report, "PROVIDER_FAILURE", self._http_category(exc.code))
        except Exception:
            return self._failed(report, "PROVIDER_FAILURE", "TRANSPORT")
        if not isinstance(body, bytes):
            return self._failed(report, "MALFORMED", "BODY_TYPE")
        if len(body) > MAX_RESPONSE_BYTES:
            return self._failed(report, "MALFORMED", "BODY_SIZE")
        report["response_sha256"] = hashlib.sha256(body).hexdigest()
        try:
            rows = json.loads(
                body.decode("utf-8"),
                object_pairs_hook=self._unique_object,
                parse_constant=self._invalid_constant,
            )
        except (UnicodeDecodeError, ValueError):
            return self._failed(report, "MALFORMED", "JSON_INVALID")
        if not isinstance(rows, list) or len(rows) > 5000:
            return self._failed(report, "MALFORMED", "ROW_SHAPE")
        report["row_count"] = len(rows)
        if not rows:
            return self._failed(report, "EMPTY", None)
        previous: date | None = None
        for row in rows:
            if not isinstance(row, dict):
                return self._failed(report, "MALFORMED", "ROW_SHAPE")
            for field in FIELDS:
                if field not in row:
                    return self._failed(report, "MISSING_FIELDS", "FIELD_MISSING")
                report["field_presence_count"][field] += 1
            value = row["date"]
            if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
                return self._failed(report, "MALFORMED", "DATE_INVALID")
            try:
                session = date.fromisoformat(value)
            except ValueError:
                return self._failed(report, "MALFORMED", "DATE_INVALID")
            if not request.start <= session < request.end:
                return self._failed(report, "MALFORMED", "DATE_WINDOW")
            if previous is not None and session <= previous:
                return self._failed(report, "MALFORMED", "DATE_ORDER")
            previous = session
            if report["first_date"] is None:
                report["first_date"] = value
            report["last_date"] = value
            prices = (row[name] for name in ("open", "high", "low", "close", "adjusted_close"))
            if not all(self._finite_number(number, positive=True) for number in prices):
                return self._failed(report, "MALFORMED", "PRICE_INVALID")
            if (
                not isinstance(row["volume"], int)
                or isinstance(row["volume"], bool)
                or row["volume"] < 0
            ):
                return self._failed(report, "MALFORMED", "VOLUME_INVALID")
            if row["low"] > row["high"] or not all(
                row["low"] <= row[name] <= row["high"] for name in ("open", "close")
            ):
                return self._failed(report, "MALFORMED", "OHLC_INCONSISTENT")
        report["status"] = "QUALIFIED"
        return report

    @staticmethod
    def _finite_number(value: object, *, positive: bool) -> bool:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        try:
            return isfinite(value) and (value > 0 if positive else value >= 0)
        except OverflowError:
            return False

    @staticmethod
    def _http_category(code: int) -> str:
        return f"HTTP_{code}" if code in (401, 403, 404, 429) else "HTTP_OTHER"

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    @staticmethod
    def _invalid_constant(value: str) -> None:
        raise ValueError("non-standard JSON constant")

    @staticmethod
    def _failed(report: dict[str, Any], status: str, category: str | None) -> dict[str, Any]:
        report["status"] = status
        report["failure_category"] = category
        # Never publish partially validated field or date evidence.
        report["first_date"] = None
        report["last_date"] = None
        report["field_presence_count"] = {field: 0 for field in FIELDS}
        return report

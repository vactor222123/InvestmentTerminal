"""Generate the bounded audited XNAS session evidence document."""

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from investment_terminal.utils.atomic_write import write_json_atomic

START = date(2025, 8, 19)
END = date(2026, 8, 18)
SOURCE_URI = "https://nasdaqtrader.com/Trader.aspx?id=Calendar"
CLOSED = {date(2025, 9, 1), date(2025, 11, 27), date(2025, 12, 25),
          date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16),
          date(2026, 4, 3), date(2026, 5, 25), date(2026, 6, 19),
          date(2026, 7, 3)}
EARLY = {date(2025, 11, 28), date(2025, 12, 24)}

FIVE_YEAR_START = date(2021, 8, 19)
FIVE_YEAR_END = END
FIVE_YEAR_SOURCE_URIS = tuple(
    [
        SOURCE_URI,
        *(
            "https://www.nasdaqtrader.com/content/technicalsupport/"
            f"{year}tradingcalendar.pdf"
            for year in range(2021, 2026)
        ),
        "https://www.nasdaq.com/holiday-trading-hours",
        "https://www.nasdaqtrader.com/TraderNews.aspx?id=ETA2025-1",
    ]
)
FIVE_YEAR_CLOSED = {
    date(2021, 9, 6), date(2021, 11, 25), date(2021, 12, 24),
    date(2022, 1, 17), date(2022, 2, 21), date(2022, 4, 15),
    date(2022, 5, 30), date(2022, 6, 20), date(2022, 7, 4),
    date(2022, 9, 5), date(2022, 11, 24), date(2022, 12, 26),
    date(2023, 1, 2), date(2023, 1, 16), date(2023, 2, 20),
    date(2023, 4, 7), date(2023, 5, 29), date(2023, 6, 19),
    date(2023, 7, 4), date(2023, 9, 4), date(2023, 11, 23),
    date(2023, 12, 25), date(2024, 1, 1), date(2024, 1, 15),
    date(2024, 2, 19), date(2024, 3, 29), date(2024, 5, 27),
    date(2024, 6, 19), date(2024, 7, 4), date(2024, 9, 2),
    date(2024, 11, 28), date(2024, 12, 25), date(2025, 1, 1),
    date(2025, 1, 9), date(2025, 1, 20), date(2025, 2, 17),
    date(2025, 4, 18), date(2025, 5, 26), date(2025, 6, 19),
    date(2025, 7, 4), *CLOSED,
}
FIVE_YEAR_EARLY = {
    date(2021, 11, 26), date(2022, 11, 25), date(2023, 7, 3),
    date(2023, 11, 24), date(2024, 7, 3), date(2024, 11, 29),
    date(2024, 12, 24), *EARLY,
}


def _build_document(
    retrieved_at: datetime,
    *,
    start: date,
    end: date,
    closed: set[date],
    early: set[date],
    version: int,
    source_uris: tuple[str, ...],
) -> dict[str, object]:
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    zone = ZoneInfo("America/New_York")
    sessions = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in closed:
            close = time(13 if current in early else 16)
            sessions.append({
                "session_key": f"XNAS:{current.isoformat()}",
                "session_date": current.isoformat(),
                "opens_at": datetime.combine(current, time(9, 30), zone).isoformat(),
                "closes_at": datetime.combine(current, close, zone).isoformat(),
            })
        current += timedelta(days=1)
    serialized = json.dumps(sessions, sort_keys=True, separators=(",", ":")).encode()
    return {
        "calendar": {"calendar_id": "XNAS", "version": version,
                     "timezone": "America/New_York",
                     "source": "NASDAQ_TRADER_CALENDAR"},
        "evidence": {"source_uri": SOURCE_URI,
                     "source_uris": list(source_uris),
                     "retrieved_at": retrieved_at.isoformat(),
                     "sessions_sha256": hashlib.sha256(serialized).hexdigest()},
        "sessions": sessions,
    }


def build_document(retrieved_at: datetime) -> dict[str, object]:
    return _build_document(
        retrieved_at,
        start=START,
        end=END,
        closed=CLOSED,
        early=EARLY,
        version=1,
        source_uris=(SOURCE_URI,),
    )


def build_five_year_document(retrieved_at: datetime) -> dict[str, object]:
    return _build_document(
        retrieved_at,
        start=FIVE_YEAR_START,
        end=FIVE_YEAR_END,
        closed=FIVE_YEAR_CLOSED,
        early=FIVE_YEAR_EARLY,
        version=2,
        source_uris=FIVE_YEAR_SOURCE_URIS,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--window",
        choices=("one-year", "five-year"),
        default="one-year",
    )
    options = parser.parse_args()
    retrieved_at = datetime.fromisoformat(options.retrieved_at.replace("Z", "+00:00"))
    builder = (
        build_five_year_document
        if options.window == "five-year"
        else build_document
    )
    write_json_atomic(options.output, builder(retrieved_at))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

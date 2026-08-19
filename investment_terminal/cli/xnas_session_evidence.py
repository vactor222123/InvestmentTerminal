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


def build_document(retrieved_at: datetime) -> dict[str, object]:
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("retrieved_at must be timezone-aware")
    zone = ZoneInfo("America/New_York")
    sessions = []
    current = START
    while current <= END:
        if current.weekday() < 5 and current not in CLOSED:
            close = time(13 if current in EARLY else 16)
            sessions.append({
                "session_key": f"XNAS:{current.isoformat()}",
                "session_date": current.isoformat(),
                "opens_at": datetime.combine(current, time(9, 30), zone).isoformat(),
                "closes_at": datetime.combine(current, close, zone).isoformat(),
            })
        current += timedelta(days=1)
    serialized = json.dumps(sessions, sort_keys=True, separators=(",", ":")).encode()
    return {
        "calendar": {"calendar_id": "XNAS", "version": 1,
                     "timezone": "America/New_York",
                     "source": "NASDAQ_TRADER_CALENDAR"},
        "evidence": {"source_uri": SOURCE_URI,
                     "retrieved_at": retrieved_at.isoformat(),
                     "sessions_sha256": hashlib.sha256(serialized).hexdigest()},
        "sessions": sessions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    retrieved_at = datetime.fromisoformat(options.retrieved_at.replace("Z", "+00:00"))
    write_json_atomic(options.output, build_document(retrieved_at))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

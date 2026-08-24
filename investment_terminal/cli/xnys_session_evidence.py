"""Generate bounded audited XNYS session evidence."""

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from investment_terminal.utils.atomic_write import write_json_atomic

START = date(2021, 8, 19)
END = date(2026, 8, 18)
SOURCE_URI = "https://www.nyse.com/markets/hours-calendars"
SOURCE_URIS = (
    SOURCE_URI,
    "https://ir.theice.com/press/news-details/2020/"
    "NYSE-Group-Announces-2021-2022-and-2023-Holiday-and-Early-"
    "Closings-Calendar/default.aspx",
    "https://ir.theice.com/press/news-details/2021/"
    "NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-"
    "Closings-Calendar/default.aspx",
    "https://ir.theice.com/press/news-details/2023/"
    "NYSE-Group-Announces-2024-2025-and-2026-Holiday-and-Early-"
    "Closings-Calendar/default.aspx",
    "https://www.nyse.com/publicdocs/nyse/markets/american-options/"
    "rule-interpretations/2025/National_Day_of_Mourning_20250102.pdf",
)
CLOSED = {
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
    date(2025, 7, 4), date(2025, 9, 1), date(2025, 11, 27),
    date(2025, 12, 25), date(2026, 1, 1), date(2026, 1, 19),
    date(2026, 2, 16), date(2026, 4, 3), date(2026, 5, 25),
    date(2026, 6, 19), date(2026, 7, 3),
}
EARLY = {
    date(2021, 11, 26), date(2022, 11, 25), date(2023, 7, 3),
    date(2023, 11, 24), date(2024, 7, 3), date(2024, 11, 29),
    date(2024, 12, 24), date(2025, 11, 28), date(2025, 12, 24),
}


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
                "session_key": f"XNYS:{current.isoformat()}",
                "session_date": current.isoformat(),
                "opens_at": datetime.combine(
                    current, time(9, 30), zone
                ).isoformat(),
                "closes_at": datetime.combine(
                    current, close, zone
                ).isoformat(),
            })
        current += timedelta(days=1)
    serialized = json.dumps(
        sessions, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "calendar": {
            "calendar_id": "XNYS",
            "version": 1,
            "timezone": "America/New_York",
            "source": "NYSE_GROUP_CALENDAR",
        },
        "evidence": {
            "source_uri": SOURCE_URI,
            "source_uris": list(SOURCE_URIS),
            "retrieved_at": retrieved_at.isoformat(),
            "sessions_sha256": hashlib.sha256(serialized).hexdigest(),
        },
        "sessions": sessions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    retrieved_at = datetime.fromisoformat(
        options.retrieved_at.replace("Z", "+00:00")
    )
    write_json_atomic(options.output, build_document(retrieved_at))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

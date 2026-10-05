"""One bounded public EODHD demo request; response bytes stay in memory."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen


MAX_RESPONSE_BYTES = 4_000_000


class EodhdDemoPriceClient:
    """Fetch only VTI.US with the published public demo token."""

    def __init__(self, fetch: Callable[[str], bytes] | None = None) -> None:
        self._fetch = fetch or self._fetch_live

    def get_daily_bytes(self, *, start: date, end: date) -> bytes:
        parameters = urlencode({
            "api_token": "demo",
            "fmt": "json",
            "period": "d",
            "order": "a",
            "from": start.isoformat(),
            "to": (end - timedelta(days=1)).isoformat(),
        })
        return self._fetch(f"https://eodhd.com/api/eod/VTI.US?{parameters}")

    @staticmethod
    def _fetch_live(url: str) -> bytes:
        with urlopen(url, timeout=20) as response:
            return response.read(MAX_RESPONSE_BYTES + 1)

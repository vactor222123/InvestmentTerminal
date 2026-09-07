from datetime import datetime, timezone

import pytest

from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from investment_terminal.models.candle import Candle
from investment_terminal.services.projected_historical_market_service import (
    ProjectedHistoricalMarketService,
)


NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


def candle():
    return Candle(symbol="AAA", resolution="D", timestamp=NOW, open_price=1,
                  high_price=1, low_price=1, close_price=1, volume=1,
                  currency="USD")


class Client:
    def __init__(self, projection): self.projection = projection; self.calls = []
    def get_candle_projection(self, **kwargs):
        self.calls.append(kwargs); return self.projection


class Repository:
    def __init__(self, inserted=1): self.inserted = inserted; self.saved = None
    def save_many(self, candles): self.saved = candles; return self.inserted


def test_persists_projection_and_returns_typed_omission_evidence():
    client = Client(YahooCandleProjection((candle(),), 1,
                    ("TRAILING_NON_FINITE_NUMERIC",)))
    repository = Repository()
    result = ProjectedHistoricalMarketService(client, repository).import_candles(
        "AAA", "D", NOW.replace(year=2016), NOW, "USD")
    assert result.downloaded == result.inserted == 1
    assert result.duplicates == 0
    assert result.omitted_trailing_count == 1
    assert result.omission_types == ("TRAILING_NON_FINITE_NUMERIC",)
    assert repository.saved == [candle()]
    assert client.calls[0]["allow_trailing_incomplete"] is True


def test_rejects_invalid_repository_count_without_success_result():
    service = ProjectedHistoricalMarketService(
        Client(YahooCandleProjection((candle(),), 0, ())), Repository(inserted=2)
    )
    with pytest.raises(RuntimeError, match="invalid inserted count"):
        service.import_candles("AAA", "D", NOW.replace(year=2016), NOW)

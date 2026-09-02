from datetime import datetime, timezone

from investment_terminal.operations.chart_currency_qualification import ChartCurrencyQualificationService
from tests.test_symbol_currency_diagnostic import checkpoint
from tests.test_symbol_currency_qualification import checksum, projection


NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)


class Client:
    def __init__(self, currency="USD"): self.currency=currency; self.calls=[]
    def get_currency(self, symbol): self.calls.append(symbol); return self.currency


def test_qualifies_one_private_symbol_and_redacts_report():
    value=projection(); client=Client()
    private, report=ChartCurrencyQualificationService(client=client,clock=lambda:NOW).run(
        value,checksum(value),checkpoint(value))
    assert client.calls==["AAA"] and private["currency"]=="USD"
    assert report["coverage"]=={"attempted_count":1,"qualified_count":1}
    assert "AAA" not in str(report) and "USD" not in str(report)

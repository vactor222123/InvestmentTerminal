"""Focused and failure-path tests for the isolated price-basis probe."""

import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from investment_terminal.cli.yahoo_price_basis_qualification import main
from investment_terminal.clients.yahoo_price_basis_client import YahooPriceBasisClient
from investment_terminal.operations.yahoo_price_basis_qualification import (
    PriceBasisQualification,
    PriceBasisRequest,
)


START = datetime(2026, 9, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 4, tzinfo=timezone.utc)


def frame():
    return pd.DataFrame(
        {
            "Close": [100.0, 101.0],
            "Adj Close": [99.0, 100.0],
            "Dividends": [0.0, 0.5],
            "Stock Splits": [0.0, 0.0],
        },
        index=pd.DatetimeIndex([START, datetime(2026, 9, 2, tzinfo=timezone.utc)]),
    )


class FakeClient:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.calls = []

    def get_daily_frame(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.value


def request():
    return PriceBasisRequest(" mcd ", START, END)


def test_adapter_makes_exactly_one_nonadjusted_actions_request():
    calls = []

    class Ticker:
        def history(self, **kwargs):
            calls.append(kwargs)
            return frame()

    result = YahooPriceBasisClient(ticker_factory=lambda symbol: Ticker()).get_daily_frame(
        symbol="MCD", start=START, end=END
    )
    assert isinstance(result, pd.DataFrame)
    assert calls == [{
        "start": START, "end": END, "interval": "1d",
        "auto_adjust": False, "actions": True, "repair": False,
        "raise_errors": True,
    }]


def test_qualification_only_reports_aggregate_shape():
    client = FakeClient(frame())
    result = PriceBasisQualification(client).qualify(request())
    assert result["status"] == "QUALIFIED"
    assert result["row_count"] == 2
    assert result["fields"]["Dividends"]["nonzero_count"] == 1
    assert len(client.calls) == 1
    assert client.calls[0]["symbol"] == "MCD"
    text = json.dumps(result)
    for secret in ("MCD", "101.0", "99.0", "0.5", "C:\\runtime"):
        assert secret not in text


def test_missing_candidate_field_is_distinct():
    value = frame().drop(columns=["Adj Close"])
    result = PriceBasisQualification(FakeClient(value)).qualify(request())
    assert result["status"] == "MISSING_FIELDS"
    assert result["fields"]["Adj Close"]["present"] is False
    assert result["fields"]["Dividends"]["present"] is True


@pytest.mark.parametrize("mutation,category", [
    (lambda f: f.assign(**{"Adj Close": [float("nan"), 1.0]}), "CANDIDATE_INVALID"),
    (lambda f: f.assign(Dividends=[-1.0, 0.0]), "CANDIDATE_INVALID"),
    (lambda f: f.assign(**{"Stock Splits": [float("inf"), 0.0]}), "CANDIDATE_INVALID"),
    (lambda f: f.set_axis([START, START], axis=0), "TIMESTAMP_INDEX"),
    (lambda f: f.set_axis([START, END], axis=0), "TIMESTAMP_WINDOW"),
    (lambda f: f.set_axis(pd.date_range("2026-09-01", periods=2), axis=0), "TIMESTAMP_INDEX"),
    (lambda f: f.assign(Close=[float("nan"), 101.0]), "CLOSE_INVALID"),
])
def test_malformed_frames_fail_closed(mutation, category):
    result = PriceBasisQualification(FakeClient(mutation(frame()))).qualify(request())
    assert result["status"] == "MALFORMED"
    assert result["failure_category"] == category
    assert all(item["valid_count"] is None for item in result["fields"].values())


def test_provider_error_never_leaks_exception_text():
    client = FakeClient(error=RuntimeError("private C:\\runtime\\data\\secret MCD 123.45"))
    result = PriceBasisQualification(client).qualify(request())
    assert result["status"] == "PROVIDER_FAILURE"
    assert result["failure_category"] == "PROVIDER_REQUEST"
    assert "secret" not in json.dumps(result)
    assert len(client.calls) == 1


def test_empty_and_nonframe_are_distinct():
    empty = PriceBasisQualification(FakeClient(pd.DataFrame())).qualify(request())
    invalid = PriceBasisQualification(FakeClient(["secret"])).qualify(request())
    assert empty["status"] == "EMPTY"
    assert empty["row_count"] == 0
    assert invalid["status"] == "MALFORMED"
    assert invalid["failure_category"] == "FRAME_TYPE"


def test_cli_writes_only_report_and_refuses_overwrite(tmp_path):
    path = tmp_path / "report.json"
    client = FakeClient(frame())
    args = ["--symbol", "MCD", "--start", "2026-09-01", "--end", "2026-09-04", "--output", str(path)]
    main(args, client=client)
    assert json.loads(path.read_text())["status"] == "QUALIFIED"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["report.json"]
    with pytest.raises(SystemExit):
        main(args, client=client)
    assert len(client.calls) == 1


def test_invalid_request_never_calls_provider(tmp_path):
    client = FakeClient(frame())
    with pytest.raises(SystemExit):
        main(["--symbol", "MCD", "--start", "2026-09-04", "--end", "2026-09-01", "--output", str(tmp_path / "x.json")], client=client)
    assert not client.calls
    assert list(tmp_path.iterdir()) == []


def test_cli_failure_writes_only_redacted_report(tmp_path, capsys):
    path = tmp_path / "failed.json"
    client = FakeClient(error=RuntimeError("secret MCD 123.45"))
    with pytest.raises(SystemExit) as exited:
        main(["--symbol", "MCD", "--start", "2026-09-01", "--end", "2026-09-04", "--output", str(path)], client=client)
    assert exited.value.code == 1
    report = path.read_text()
    assert json.loads(report)["status"] == "PROVIDER_FAILURE"
    assert "MCD" not in report + capsys.readouterr().out
    assert "secret" not in report
    assert sorted(item.name for item in tmp_path.iterdir()) == ["failed.json"]

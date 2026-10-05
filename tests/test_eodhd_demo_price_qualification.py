"""Focused and failure-path checks for the public, non-persistent demo probe."""

import hashlib
import json
from datetime import date
from urllib.error import HTTPError

import pytest

from investment_terminal.cli.eodhd_demo_price_qualification import main
from investment_terminal.clients.eodhd_demo_price_client import (
    MAX_RESPONSE_BYTES,
    EodhdDemoPriceClient,
)
from investment_terminal.operations.eodhd_demo_price_qualification import (
    DemoPriceRequest,
    EodhdDemoPriceQualification,
)


START = date(2026, 9, 1)
END = date(2026, 9, 4)


def rows():
    return [
        {"date": "2026-09-01", "open": 100.0, "high": 102.0, "low": 99.0,
         "close": 101.0, "adjusted_close": 98.0, "volume": 500},
        {"date": "2026-09-02", "open": 101.0, "high": 103.0, "low": 100.0,
         "close": 102.0, "adjusted_close": 99.0, "volume": 0},
    ]


def body(value=None):
    return json.dumps(rows() if value is None else value).encode("utf-8")


class FakeClient:
    def __init__(self, value=None, error=None):
        self.value = body() if value is None else value
        self.error = error
        self.calls = []

    def get_daily_bytes(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.value


def qualify(value=None, error=None):
    return EodhdDemoPriceQualification(FakeClient(value, error)).qualify(
        DemoPriceRequest(START, END)
    )


def test_adapter_only_requests_public_vti_demo_and_inclusive_provider_end():
    calls = []
    client = EodhdDemoPriceClient(fetch=lambda url: calls.append(url) or body())
    assert client.get_daily_bytes(start=START, end=END) == body()
    assert calls == [
        "https://eodhd.com/api/eod/VTI.US?api_token=demo&fmt=json&period=d"
        "&order=a&from=2026-09-01&to=2026-09-03"
    ]


def test_qualified_report_contains_checksum_and_aggregates_but_no_prices():
    client = FakeClient()
    result = EodhdDemoPriceQualification(client).qualify(DemoPriceRequest(START, END))
    assert result["status"] == "QUALIFIED"
    assert result["qualification_scope"] == "SOURCE_FIELD_SHAPE_ONLY"
    assert result["row_count"] == 2
    assert result["first_date"] == "2026-09-01"
    assert result["last_date"] == "2026-09-02"
    assert set(result["field_presence_count"].values()) == {2}
    assert result["response_sha256"] == hashlib.sha256(body()).hexdigest()
    assert client.calls == [{"start": START, "end": END}]
    rendered = json.dumps(result)
    for secret in ("api_token", "101.0", "98.0", "500", "C:\\runtime"):
        assert secret not in rendered


@pytest.mark.parametrize("source,status,category", [
    (b"not-json", "MALFORMED", "JSON_INVALID"),
    (b"{}", "MALFORMED", "ROW_SHAPE"),
    (body([]), "EMPTY", None),
    (body([{"date": "2026-09-01"}]), "MISSING_FIELDS", "FIELD_MISSING"),
    (body([{**rows()[0], "adjusted_close": None}]), "MALFORMED", "PRICE_INVALID"),
    (body([{**rows()[0], "close": True}]), "MALFORMED", "PRICE_INVALID"),
    (body([{**rows()[0], "volume": -1}]), "MALFORMED", "VOLUME_INVALID"),
    (body([{**rows()[0], "volume": 0.5}]), "MALFORMED", "VOLUME_INVALID"),
    (body([{**rows()[0], "open": 200}]), "MALFORMED", "OHLC_INCONSISTENT"),
    (body([{**rows()[0], "date": "2026-09-04"}]), "MALFORMED", "DATE_WINDOW"),
    (body([rows()[1], rows()[0]]), "MALFORMED", "DATE_ORDER"),
    (body([rows()[0], rows()[0]]), "MALFORMED", "DATE_ORDER"),
    (body([{**rows()[0], "date": "2026-09-99"}]), "MALFORMED", "DATE_INVALID"),
    ("secret", "MALFORMED", "BODY_TYPE"),
    (b'[{"date":"2026-09-01","date":"2026-09-02"}]', "MALFORMED", "JSON_INVALID"),
    (b'[{"date":NaN}]', "MALFORMED", "JSON_INVALID"),
    (b"x" * (MAX_RESPONSE_BYTES + 1), "MALFORMED", "BODY_SIZE"),
], ids=[
    "invalid-json", "wrong-root", "empty", "missing-fields", "null-adjusted",
    "boolean-price", "negative-volume", "fractional-volume", "ohlc",
    "outside-window", "unordered", "duplicate-date", "invalid-date",
    "wrong-body-type", "duplicate-json-key", "nonstandard-nan", "oversize",
])
def test_bad_response_fails_closed_without_partial_values(source, status, category):
    result = qualify(source)
    assert (result["status"], result["failure_category"]) == (status, category)
    assert result["first_date"] is None and result["last_date"] is None
    assert set(result["field_presence_count"].values()) == {0}


@pytest.mark.parametrize("code,expected", [(401, "HTTP_401"), (403, "HTTP_403"),
                                            (404, "HTTP_404"), (429, "HTTP_429"),
                                            (500, "HTTP_OTHER")])
def test_http_error_is_classified_without_url_or_body(code, expected):
    error = HTTPError("https://secret.example/?api_token=private", code, "secret", None, None)
    result = qualify(error=error)
    assert result["status"] == "PROVIDER_FAILURE"
    assert result["failure_category"] == expected
    assert "secret" not in json.dumps(result)
    assert "private" not in json.dumps(result)


def test_transport_error_is_redacted():
    result = qualify(error=RuntimeError("secret URL and price 123.45"))
    assert result["failure_category"] == "TRANSPORT"
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("start,end", [
    (END, START),
    (START, START),
    (date(2010, 1, 1), date(2026, 1, 1)),
])
def test_invalid_window_is_rejected_before_provider(start, end):
    with pytest.raises(ValueError, match="window"):
        DemoPriceRequest(start, end)


def test_cli_writes_only_redacted_report_and_refuses_overwrite(tmp_path, capsys):
    client = FakeClient()
    output = tmp_path / "report.json"
    args = ["--start", "2026-09-01", "--end", "2026-09-04", "--output", str(output)]
    main(args, client=client)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "QUALIFIED"
    rendered = output.read_text(encoding="utf-8") + capsys.readouterr().out
    assert "101.0" not in rendered and "api_token" not in rendered
    with pytest.raises(SystemExit):
        main(args, client=client)
    assert len(client.calls) == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == ["report.json"]


def test_cli_invalid_window_or_date_makes_no_request_or_file(tmp_path):
    client = FakeClient()
    output = tmp_path / "report.json"
    for start, end in (("2026-09-04", "2026-09-01"), ("2026-09-99", "2026-09-04")):
        with pytest.raises(SystemExit):
            main(["--start", start, "--end", end, "--output", str(output)], client=client)
    assert client.calls == []
    assert not output.exists()


def test_cli_provider_failure_writes_only_redacted_report(tmp_path, capsys):
    client = FakeClient(error=RuntimeError("private token=secret price=123.45"))
    output = tmp_path / "failed.json"
    with pytest.raises(SystemExit) as exited:
        main(["--start", "2026-09-01", "--end", "2026-09-04", "--output", str(output)], client=client)
    assert exited.value.code == 1
    rendered = output.read_text(encoding="utf-8") + capsys.readouterr().out
    assert json.loads(output.read_text())["failure_category"] == "TRANSPORT"
    assert "secret" not in rendered and "123.45" not in rendered


def test_cli_atomic_write_failure_does_not_claim_success(tmp_path, monkeypatch):
    output = tmp_path / "report.json"

    def fail_write(*args, **kwargs):
        raise OSError("disk failed")

    monkeypatch.setattr(
        "investment_terminal.cli.eodhd_demo_price_qualification.write_json_atomic",
        fail_write,
    )
    with pytest.raises(OSError, match="disk failed"):
        main(["--start", "2026-09-01", "--end", "2026-09-04", "--output", str(output)], client=FakeClient())
    assert not output.exists()

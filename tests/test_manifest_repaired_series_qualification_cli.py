import json

from investment_terminal.cli import manifest_repaired_series_qualification as cli
from investment_terminal.utils.exceptions import APIError
from tests.test_manifest_bound_market_batch import NOW, manifest
from tests.test_manifest_repaired_series_qualification import Client
from yfinance.exceptions import YFRateLimitError


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def prepare(tmp_path):
    value, checksum = manifest()
    checkpoint = {
        "schema_version": 1,
        "request_checksum": value["batches"][0]["request_checksum"],
        "outcomes": {
            "AAA": {
                "status": "FAILED",
                "failure_type": "YahooCandleInvalidResponseError",
            }
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    return checksum, checkpoint_path


def test_cli_atomically_writes_qualified_redacted_report(tmp_path, monkeypatch):
    checksum, checkpoint_path = prepare(tmp_path)
    before = checkpoint_path.read_bytes()
    calls = []
    real_write = cli.write_json_atomic

    def write(path, payload):
        calls.append((path, payload["status"]))
        return real_write(path, payload)

    monkeypatch.setattr(cli, "write_json_atomic", write)
    result = cli.main(
        arguments(tmp_path, checksum), client=Client(), clock=lambda: NOW
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert calls == [(tmp_path / "report.json", "QUALIFIED")]
    assert report["schema_version"] == 2
    assert report["failure"] is None
    assert report["qualification_identity"] == (
        "MANIFEST_REPAIRED_SERIES_QUALIFICATION"
    )
    assert report["manifest_checksum"] == checksum
    assert checkpoint_path.read_bytes() == before
    assert "AAA" not in report_text


def test_rate_limit_writes_normalized_redacted_failure(tmp_path):
    checksum, _ = prepare(tmp_path)

    class RateLimitedClient:
        def get_daily_frame(self, **kwargs):
            try:
                raise YFRateLimitError()
            except YFRateLimitError as exc:
                raise APIError("private provider detail") from exc

    result = cli.main(
        arguments(tmp_path, checksum),
        client=RateLimitedClient(),
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["schema_version"] == 2
    assert report["failure"]["category"] == "RATE_LIMITED"
    assert report["failure"]["exception_type_chain"] == [
        "investment_terminal.utils.exceptions.APIError",
        "yfinance.exceptions.YFRateLimitError",
    ]
    assert "private provider detail" not in report_text
    assert "AAA" not in report_text


def test_invalid_checkpoint_fails_before_provider_access(tmp_path):
    checksum, _ = prepare(tmp_path)
    (tmp_path / "checkpoint.json").write_text(
        json.dumps({"schema_version": 1, "outcomes": {}}), encoding="utf-8"
    )
    client = Client()

    result = cli.main(
        arguments(tmp_path, checksum), client=client, clock=lambda: NOW
    )

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["failure"]["category"] == "INVALID_RESPONSE"
    assert report["failure"]["exception_type_chain"] == ["builtins.ValueError"]
    assert client.calls == []


def test_unapproved_failure_type_is_redacted_from_strict_json_report(tmp_path):
    checksum, _ = prepare(tmp_path)
    hidden_type = type(
        "HiddenError",
        (Exception,),
        {"__module__": "private_provider.internal"},
    )

    class UnexpectedClient:
        def get_daily_frame(self, **kwargs):
            try:
                raise hidden_type("private payload and C:/private/path")
            except hidden_type as exc:
                raise APIError("private provider detail") from exc

    result = cli.main(
        arguments(tmp_path, checksum),
        client=UnexpectedClient(),
        clock=lambda: NOW,
    )

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    serialized = json.dumps(report, allow_nan=False)
    assert result == 1
    assert report["failure"] == {
        "category": "UNEXPECTED",
        "exception_type_chain": [
            "investment_terminal.utils.exceptions.APIError",
            "UNRECOGNIZED_EXCEPTION_TYPE",
        ],
        "reason": "Manifest repaired-series qualification failed",
    }
    assert "private payload" not in serialized
    assert "private provider detail" not in serialized
    assert "private_provider" not in serialized
    assert "private/path" not in serialized
    assert "AAA" not in serialized

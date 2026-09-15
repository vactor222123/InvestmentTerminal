import json

from investment_terminal.cli import manifest_partial_failure_qualification as cli
from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from tests.test_manifest_partial_failure_qualification import (
    NOW,
    Client,
    candle,
    evidence,
)


def prepare(tmp_path):
    value, checksum, selection, checkpoint, selected = evidence()
    (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )
    return checksum, selection, selected


def arguments(tmp_path, checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_writes_redacted_qualified_report(tmp_path):
    checksum, selection, selected = prepare(tmp_path)
    client = Client(YahooCandleProjection((candle(selected, selection),), 0, ()))

    result = cli.main(arguments(tmp_path, checksum), client=client, clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 0
    assert report["status"] == "QUALIFIED"
    assert report["batch_index"] == 1
    assert selected.symbol not in report_text


def test_cli_preflight_failure_makes_no_provider_call(tmp_path):
    checksum, _, _ = prepare(tmp_path)
    checkpoint = json.loads(
        (tmp_path / "checkpoint.json").read_text(encoding="utf-8")
    )
    checkpoint["request_checksum"] = "0" * 64
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )
    client = Client(YahooCandleProjection((), 0, ()))

    result = cli.main(arguments(tmp_path, checksum), client=client, clock=lambda: NOW)

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["status"] == "FAILED"
    assert report["selection"] is None
    assert report["failure"]["category"] == "INVALID_RESPONSE"
    assert client.calls == []


def test_cli_checkpoint_preflight_precedes_live_client_composition(
    tmp_path, monkeypatch
):
    checksum, _, _ = prepare(tmp_path)
    checkpoint = json.loads(
        (tmp_path / "checkpoint.json").read_text(encoding="utf-8")
    )
    checkpoint["request_checksum"] = "0" * 64
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )

    class ClientMustNotOpen:
        def __init__(self, **kwargs):
            raise AssertionError("live client opened")

    monkeypatch.setattr(cli, "YahooFinanceClient", ClientMustNotOpen)
    result = cli.main(arguments(tmp_path, checksum), clock=lambda: NOW)

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert result == 1
    assert "live client opened" not in report_text
    assert not (tmp_path / "cache").exists()


def test_cli_rejects_manifest_mismatch_before_selection(tmp_path):
    checksum, _, _ = prepare(tmp_path)
    client = Client(YahooCandleProjection((), 0, ()))
    result = cli.main(
        arguments(tmp_path, "0" * 64), client=client, clock=lambda: NOW
    )
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["manifest_checksum"] is None
    assert report["failure"]["exception_type_chain"] == ["builtins.ValueError"]
    assert client.calls == []

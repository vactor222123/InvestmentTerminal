from hashlib import sha256
import json

from investment_terminal.cli import manifest_partial_timeout_retry as cli
from investment_terminal.clients.yahoo_finance_client import YahooCandleProjection
from investment_terminal.models.candle import Candle
from investment_terminal.utils.exceptions import APIError
from tests.test_manifest_partial_timeout_retry import NOW, evidence


class Client:
    def __init__(self):
        self.calls = []

    def get_candle_projection(
        self,
        *,
        symbol,
        resolution,
        start,
        end,
        currency,
        allow_trailing_incomplete,
    ):
        self.calls.append(symbol)
        candle = Candle(
            symbol=symbol,
            resolution=resolution,
            timestamp=end.replace(day=end.day - 1),
            open_price=1,
            high_price=1,
            low_price=1,
            close_price=1,
            volume=1,
            currency=currency,
        )
        return YahooCandleProjection((candle,), 0, ())


class TimeoutClient:
    def __init__(self):
        self.calls = []

    def get_candle_projection(self, **kwargs):
        self.calls.append(kwargs["symbol"])
        error = APIError("private")
        error.__cause__ = TimeoutError("private")
        raise error


def prepare(tmp_path):
    value, checksum, _, checkpoint, symbols, raw, inventory_checksum = evidence()
    (tmp_path / "manifest.json").write_text(
        json.dumps(value), encoding="utf-8"
    )
    (tmp_path / "checkpoint.json").write_text(
        json.dumps(checkpoint), encoding="utf-8"
    )
    (tmp_path / "inventory.json").write_bytes(raw)
    return checksum, inventory_checksum, symbols


def arguments(tmp_path, checksum, inventory_checksum):
    return [
        "--manifest", str(tmp_path / "manifest.json"),
        "--manifest-checksum", checksum,
        "--batch-index", "1",
        "--checkpoint", str(tmp_path / "checkpoint.json"),
        "--inventory", str(tmp_path / "inventory.json"),
        "--inventory-checksum", inventory_checksum,
        "--database", str(tmp_path / "market.db"),
        "--cache-directory", str(tmp_path / "cache"),
        "--report-output", str(tmp_path / "report.json"),
    ]


def test_cli_retries_only_timeout_and_atomically_writes_redacted_report(tmp_path):
    checksum, inventory_checksum, symbols = prepare(tmp_path)
    client = Client()

    result = cli.main(
        arguments(tmp_path, checksum, inventory_checksum),
        client=client,
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    checkpoint = json.loads(
        (tmp_path / "checkpoint.json").read_text(encoding="utf-8")
    )
    assert result == 0
    assert client.calls == [symbols[3]]
    assert report["status"] == "READY_FOR_SWEEP"
    assert report["retry_result"]["status"] == "SUCCESS"
    assert checkpoint["outcomes"][symbols[3]]["status"] == "SUCCESS"
    assert checkpoint["outcomes"][symbols[1]]["status"] == "FAILED"
    assert checkpoint["outcomes"][symbols[2]]["status"] == "FAILED"
    assert all(symbol not in report_text for symbol in symbols)
    assert str(tmp_path) not in report_text


def test_invalid_inventory_fails_before_database_or_provider(tmp_path, monkeypatch):
    checksum, inventory_checksum, symbols = prepare(tmp_path)
    inventory = json.loads((tmp_path / "inventory.json").read_text("utf-8"))
    inventory["coverage"]["missing_count"] += 1
    changed = json.dumps(inventory).encode("utf-8")
    (tmp_path / "inventory.json").write_bytes(changed)

    class DatabaseMustNotOpen:
        def __init__(self, path):
            raise AssertionError("database opened")

    monkeypatch.setattr(cli, "Database", DatabaseMustNotOpen)
    client = Client()
    result = cli.main(
        arguments(tmp_path, checksum, sha256(changed).hexdigest()),
        client=client,
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert client.calls == []
    assert report["status"] == "FAILED"
    assert report["failure"]["category"] == "VALIDATION_OR_IO_ERROR"
    assert "database opened" not in report_text
    assert all(symbol not in report_text for symbol in symbols)


def test_cli_persists_repeated_timeout_and_returns_nonzero(tmp_path):
    checksum, inventory_checksum, symbols = prepare(tmp_path)
    client = TimeoutClient()

    result = cli.main(
        arguments(tmp_path, checksum, inventory_checksum),
        client=client,
        clock=lambda: NOW,
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    checkpoint = json.loads(
        (tmp_path / "checkpoint.json").read_text(encoding="utf-8")
    )
    assert result == 1
    assert client.calls == [symbols[3]]
    assert report["status"] == "BLOCKED"
    assert report["retry_result"]["failure_category"] == "TIMEOUT"
    assert checkpoint["outcomes"][symbols[3]]["status"] == "FAILED"
    assert all(symbol not in report_text for symbol in symbols)


def test_checkpoint_write_failure_is_redacted_and_nonzero(tmp_path):
    checksum, inventory_checksum, symbols = prepare(tmp_path)
    original = (tmp_path / "checkpoint.json").read_bytes()
    client = Client()

    result = cli.main(
        arguments(tmp_path, checksum, inventory_checksum),
        client=client,
        clock=lambda: NOW,
        checkpoint_writer=lambda path, value: (_ for _ in ()).throw(
            OSError("private")
        ),
    )

    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert client.calls == [symbols[3]]
    assert (tmp_path / "checkpoint.json").read_bytes() == original
    assert report["status"] == "FAILED"
    assert report["failure"]["category"] == "CHECKPOINT_WRITE_FAILED"
    assert "OSError" not in report_text
    assert all(symbol not in report_text for symbol in symbols)

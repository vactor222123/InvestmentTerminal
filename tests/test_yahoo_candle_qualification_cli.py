"""CLI tests for Yahoo historical-candle qualification."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.yahoo_candle_qualification import main
from investment_terminal.models.candle import Candle
from investment_terminal.utils.exceptions import APIError


START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 3, tzinfo=timezone.utc)


class Client:
    def __init__(self, result) -> None:
        self.result = result

    def get_candles(self, **kwargs):
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def candle() -> Candle:
    return Candle(
        symbol="MSFT",
        resolution="D",
        timestamp=START + timedelta(days=1),
        open_price=100,
        high_price=102,
        low_price=99,
        close_price=101,
        volume=1000,
        currency="USD",
    )


def arguments(output: Path) -> list[str]:
    return [
        "--symbol",
        "MSFT",
        "--resolution",
        "D",
        "--currency",
        "USD",
        "--start",
        START.isoformat(),
        "--end",
        END.isoformat(),
        "--output",
        str(output),
        "--json",
    ]


def run_clock():
    values = iter((START, START + timedelta(seconds=1)))
    return lambda: next(values)


def test_cli_atomically_exports_success_report(
    tmp_path: Path,
    capsys,
) -> None:
    output = tmp_path / "nested" / "qualification.json"
    main(arguments(output), client=Client([candle()]), clock=run_clock())

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == json.loads(capsys.readouterr().out)
    assert payload["status"] == "SUCCESS"


def test_cli_persists_failure_before_nonzero_exit(tmp_path: Path) -> None:
    output = tmp_path / "qualification.json"

    with pytest.raises(SystemExit) as error:
        main(
            arguments(output),
            client=Client(APIError("provider unavailable")),
            clock=run_clock(),
        )

    assert error.value.code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["failure"]["type"] == "APIError"


def test_cli_rejects_naive_datetime(tmp_path: Path) -> None:
    values = arguments(tmp_path / "report.json")
    values[values.index(START.isoformat())] = "2026-08-01T00:00:00"

    with pytest.raises(SystemExit) as error:
        main(values, client=Client([]), clock=run_clock())

    assert error.value.code == 2


def test_live_cli_requires_explicit_cache_directory(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        main(arguments(tmp_path / "report.json"))

    assert error.value.code == 2

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_terminal.cli.transaction_csv_qualification import main
from investment_terminal.portfolio.transaction_csv_parser import (
    PortfolioTransactionCsvParser,
)


NOW = datetime(2026, 8, 25, 12, tzinfo=timezone.utc)
HEADER = ",".join(PortfolioTransactionCsvParser.COLUMNS)


def clock():
    values = iter((NOW, NOW + timedelta(seconds=1)))
    return values.__next__


def arguments(source: Path, output: Path) -> list[str]:
    return [
        "--input", str(source), "--qualified-at", NOW.isoformat(),
        "--output", str(output), "--json",
    ]


def test_cli_atomically_exports_success_without_database(
    tmp_path: Path, capsys
) -> None:
    source = tmp_path / "transactions.csv"
    source.write_text(
        HEADER + "\nexample,FEE,2026-01-01T10:00:00Z,EUR,,,,,,,,,,1,ref\n",
        encoding="utf-8",
    )
    output = tmp_path / "nested" / "qualification.json"
    main(arguments(source, output), clock=clock())
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == json.loads(capsys.readouterr().out)
    assert payload["status"] == "SUCCESS"
    assert not any(tmp_path.glob("*.db"))


def test_cli_persists_failure_before_nonzero_exit(tmp_path: Path) -> None:
    output = tmp_path / "qualification.json"
    with pytest.raises(SystemExit) as error:
        main(arguments(tmp_path / "missing.csv", output), clock=clock())
    assert error.value.code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["failure"]["type"] == "FileNotFoundError"


def test_cli_rejects_naive_qualification_time(tmp_path: Path) -> None:
    values = arguments(tmp_path / "source.csv", tmp_path / "report.json")
    values[values.index(NOW.isoformat())] = "2026-08-25T12:00:00"
    with pytest.raises(SystemExit) as error:
        main(values, clock=clock())
    assert error.value.code == 2

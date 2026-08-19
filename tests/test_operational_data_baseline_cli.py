"""CLI tests for operational data baseline export."""

import json
from pathlib import Path

from investment_terminal.cli.operational_data_baseline import main


def test_cli_prints_machine_readable_report(capsys) -> None:
    main(["--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["refresh_observability"] == "UNMEASURED"


def test_cli_atomically_exports_complete_report(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "baseline.json"
    main(["--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert len(payload["stores"]) == 8

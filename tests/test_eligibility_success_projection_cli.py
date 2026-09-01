import json

from investment_terminal.cli.eligibility_success_projection import main
from tests.test_eligibility_success_projection import NOW, complete_checkpoint, request


def _write_inputs(tmp_path):
    scan_request = request()
    universe_path = tmp_path / "universe.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    universe_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "universe_identity": "BROAD_US_LISTED_SECURITIES",
                "source_identity": "NASDAQ_TRADER_SYMBOL_DIRECTORY",
                "archive_sha256": {
                    "NASDAQ_LISTED": "a" * 64,
                    "OTHER_LISTED": "b" * 64,
                },
                "members": [
                    {
                        "source": item.source,
                        "source_symbol": item.source_symbol,
                        "yahoo_symbol": item.yahoo_symbol,
                        "security_name": item.yahoo_symbol,
                        "listing_code": "Q",
                        "is_etf": False,
                    }
                    for item in scan_request.members
                ],
            }
        ),
        encoding="utf-8",
    )
    checkpoint_path.write_text(
        json.dumps(complete_checkpoint(scan_request)),
        encoding="utf-8",
    )
    return universe_path, checkpoint_path


def test_cli_writes_private_projection_and_redacted_report(tmp_path):
    universe_path, checkpoint_path = _write_inputs(tmp_path)
    private_path = tmp_path / "private.json"
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--universe",
            str(universe_path),
            "--checkpoint",
            str(checkpoint_path),
            "--private-output",
            str(private_path),
            "--report-output",
            str(report_path),
            "--window-end",
            NOW.isoformat(),
        ],
        clock=lambda: NOW,
    )

    private = json.loads(private_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert [item["yahoo_symbol"] for item in private["members"]] == ["AAA", "CCC"]
    assert report["status"] == "SUCCESS"
    assert "AAA" not in report_path.read_text(encoding="utf-8")


def test_cli_failure_writes_only_redacted_report(tmp_path):
    universe_path, checkpoint_path = _write_inputs(tmp_path)
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["outcomes"].pop("NASDAQ_LISTED:CCC")
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    private_path = tmp_path / "private.json"
    report_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--universe",
            str(universe_path),
            "--checkpoint",
            str(checkpoint_path),
            "--private-output",
            str(private_path),
            "--report-output",
            str(report_path),
            "--window-end",
            NOW.isoformat(),
        ],
        clock=lambda: NOW,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert not private_path.exists()
    assert report["status"] == "FAILED"
    assert report["failure"] == {
        "type": "ValueError",
        "reason": "Eligibility success projection failed",
    }
    assert "CCC" not in report_path.read_text(encoding="utf-8")


def test_cli_private_write_failure_is_redacted(tmp_path):
    universe_path, checkpoint_path = _write_inputs(tmp_path)
    private_path = tmp_path / "private.json"
    report_path = tmp_path / "report.json"

    def writer(path, payload):
        if path == private_path:
            raise OSError("private path detail")
        path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = main(
        [
            "--universe",
            str(universe_path),
            "--checkpoint",
            str(checkpoint_path),
            "--private-output",
            str(private_path),
            "--report-output",
            str(report_path),
            "--window-end",
            NOW.isoformat(),
        ],
        clock=lambda: NOW,
        writer=writer,
    )

    report_text = report_path.read_text(encoding="utf-8")
    assert exit_code == 1
    assert not private_path.exists()
    assert "private path detail" not in report_text
    assert json.loads(report_text)["failure"]["type"] == "OSError"

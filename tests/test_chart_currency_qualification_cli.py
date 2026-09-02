import json

from investment_terminal.cli.chart_currency_qualification import main
from tests.test_chart_currency_qualification import Client, NOW
from tests.test_symbol_currency_diagnostic import checkpoint
from tests.test_symbol_currency_qualification import checksum, projection


def test_cli_writes_private_evidence_and_redacted_report(tmp_path):
    value=projection(); source=tmp_path/"projection.json"; check=tmp_path/"checkpoint.json"
    private=tmp_path/"private.json"; report=tmp_path/"report.json"
    source.write_text(json.dumps(value),encoding="utf-8")
    check.write_text(json.dumps(checkpoint(value)),encoding="utf-8")
    code=main(["--projection",str(source),"--projection-checksum",checksum(value),
        "--checkpoint",str(check),"--private-output",str(private),
        "--report-output",str(report)],client=Client(),clock=lambda:NOW)
    assert code==0 and private.exists()
    text=report.read_text(encoding="utf-8")
    assert "AAA" not in text and "USD" not in text


def test_cli_failure_is_redacted(tmp_path):
    report=tmp_path/"report.json"
    code=main(["--projection",str(tmp_path/"secret.json"),"--projection-checksum","x",
        "--checkpoint",str(tmp_path/"private.json"),"--private-output",str(tmp_path/"out.json"),
        "--report-output",str(report)],clock=lambda:NOW)
    text=report.read_text(encoding="utf-8")
    assert code==1 and "secret.json" not in text and "private.json" not in text

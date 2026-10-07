from hashlib import sha256
import json
from pathlib import Path

import pytest

from investment_terminal.cli import portfolio_split_collect as module
from tests.test_portfolio_split_collect import case
from tests.test_split_adjustment import at
from tests.test_position_reconstruction import WORLD, EM


def diagnostic(capsys):
    output = capsys.readouterr()
    lines = [line for line in output.out.splitlines() if line.startswith("PREFLIGHT_RESULT: ")]
    assert len(lines) == 1
    assert "SECRET" not in output.out + output.err
    return json.loads(lines[0].split(": ", 1)[1])


def forbidden(*args, **kwargs):
    pytest.fail("Preflight must not call collector or writer")


def file_state(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("blocked", [False, True])
def test_successful_preflight_is_read_only_and_never_calls_provider(tmp_path, capsys, blocked):
    args, source, directory, report = case(tmp_path)
    if blocked:
        source.write_text(source.read_text().replace(",ETF,", ",BOND,"))
    before = file_state(tmp_path)
    dirs = set(tmp_path.rglob("*"))
    assert module.main(args + ["--preflight-only"], collector=forbidden,
                       writer=forbidden, clock=lambda: at(22)) == 0
    result = diagnostic(capsys)
    assert result["status"] == ("READY_WITH_BLOCKERS" if blocked else "READY")
    assert result["counts"]["blocked_instrument_count"] == int(blocked)
    assert result["counts"]["pending_instrument_count"] == int(not blocked)
    assert result["collection_started"] is False
    assert file_state(tmp_path) == before and set(tmp_path.rglob("*")) == dirs
    assert not directory.exists() and not report.exists()
    for secret in (str(source), WORLD.isin, "WORLD", "100.0"):
        assert secret not in json.dumps(result)


@pytest.mark.parametrize("dry", [False, True])
@pytest.mark.parametrize("failure,category", [
    ("absent", "CSV_NOT_FOUND"), ("invalid", "CSV_NOT_FOUND"),
    ("ambiguous", "CSV_AMBIGUOUS"), ("large", "CSV_SIZE_LIMIT"),
    ("count", "CSV_FILE_LIMIT"), ("duplicate", "DUPLICATE_TRANSACTION_IDS"),
    ("no_trades", "NO_TRADE_INSTRUMENTS"), ("budget", "INSTRUMENT_BUDGET"),
    ("invalid_limit", "INVALID_INSTRUMENT_LIMIT"), ("age", "INVALID_AGE_LIMIT"),
    ("end", "INVALID_END_DATE"), ("future", "FUTURE_END_DATE"),
    ("missing_root", "INPUT_DIRECTORY_MISSING"), ("relative", "PATH_NOT_ABSOLUTE_OR_SYMLINK"),
    ("report", "REPORT_EXISTS"), ("private", "PRIVATE_SELECTION_EXISTS"),
    ("lock", "OUTPUT_LOCK_EXISTS"), ("directory", "OUTPUT_DIRECTORY_INVALID"),
    ("snapshot_root", "SNAPSHOT_INPUT_OVERLAP"), ("cache", "CACHE_SNAPSHOT_OVERLAP"),
    ("report_overlap", "REPORT_PRIVATE_OVERLAP"),
])
def test_specific_failure_categories_are_shared_and_private(tmp_path, capsys, failure, category, dry):
    args, source, directory, report = case(tmp_path)

    def option(name, value):
        args[args.index(name) + 1] = str(value)

    if failure == "absent": source.unlink()
    if failure == "invalid": source.write_text("SECRET invalid CSV")
    if failure == "ambiguous": source.with_name("copy.csv").write_bytes(source.read_bytes())
    if failure == "large": source.write_bytes(b"x" * 4_000_001)
    if failure == "count":
        for index in range(100): source.with_name(f"invalid-{index:03d}.csv").write_text("invalid")
    if failure == "duplicate":
        text = source.read_text()
        source.write_text(text + text.splitlines()[1] + "\n")
    if failure == "no_trades": source.write_text(source.read_text().splitlines()[0] + "\n")
    if failure == "budget":
        text = source.read_text()
        row = text.splitlines()[1].replace("b,BUY", "b2,BUY").replace("WORLD", "EM").replace(WORLD.isin, EM.isin)
        source.write_text(text + row + "\n")
        args += ["--max-instruments", "1"]
    if failure == "invalid_limit": args += ["--max-instruments", "51"]
    if failure == "age": args += ["--maximum-age-days", "0"]
    if failure == "end": option("--end", "SECRET-invalid-date")
    if failure == "future": option("--end", "2026-08-30")
    if failure == "missing_root": option("--transactions-directory", tmp_path / "missing")
    if failure == "relative": option("--transactions-directory", "relative")
    if failure == "report":
        report.parent.mkdir()
        report.write_text("KEEP")
    if failure == "private":
        directory.mkdir()
        token = sha256(str(report.resolve()).encode("utf-8")).hexdigest()[:24]
        (directory / (token + "-selection.json")).write_text("KEEP")
    if failure == "lock":
        directory.mkdir()
        (directory / ".portfolio-actions.lock").write_text("KEEP")
    if failure == "directory": (tmp_path / "cache").write_text("KEEP")
    if failure == "snapshot_root": option("--snapshot-directory", source.parent)
    if failure == "cache": option("--cache-directory", directory)
    if failure == "report_overlap": option("--report-output", source.parent / "report.json")
    before = file_state(tmp_path)
    paths = set(tmp_path.rglob("*"))
    assert module.main(args + (["--preflight-only"] if dry else []), collector=forbidden,
                       writer=forbidden, clock=lambda: at(22)) == 1
    data = diagnostic(capsys)
    assert data["failure_category"] == category
    assert data["status"] == "FAILED" and data["collection_started"] is False
    if failure == "budget": assert data["counts"] == {"instrument_count": 2, "maximum_instruments": 1}
    if failure == "ambiguous": assert data["counts"]["valid_csv_count"] == 2
    if failure == "invalid": assert data["counts"]["invalid_csv_count"] == 1
    if failure == "duplicate": assert data["counts"]["duplicate_id_count"] == 1
    assert file_state(tmp_path) == before and set(tmp_path.rglob("*")) == paths


@pytest.mark.parametrize("failure,category", [
    ("read", "CSV_READ_ERROR"), ("symlink", "CSV_SYMLINK"),
    ("changed", "CSV_CHANGED"), ("unexpected", "PREFLIGHT_UNEXPECTED"),
    ("clock", "INVALID_CLOCK"),
])
def test_failure_injection_does_not_leak_exception_or_contact_provider(tmp_path, monkeypatch, capsys, failure, category):
    args, source, _, _ = case(tmp_path)
    clock = lambda: at(22)
    if failure == "read":
        original = Path.read_bytes

        def read(path):
            if path == source: raise PermissionError("SECRET path")
            return original(path)

        monkeypatch.setattr(Path, "read_bytes", read)
    if failure == "symlink":
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda p: p == source or original(p))
    if failure == "changed":
        original = module.PortfolioTransactionCsvParser.load

        def changed(path, **kwargs):
            value = original(path, **kwargs)
            path.write_bytes(path.read_bytes() + b"\n")
            return value

        monkeypatch.setattr(module.PortfolioTransactionCsvParser, "load", changed)
    if failure == "unexpected":
        def explode(*args): raise RuntimeError("SECRET internal")
        monkeypatch.setattr(module, "discover_transactions", explode)
    if failure == "clock": clock = lambda: at(22).replace(tzinfo=None)
    assert module.main(args + ["--preflight-only"], collector=forbidden,
                       writer=forbidden, clock=clock) == 1
    assert diagnostic(capsys)["failure_category"] == category

"""Fail-closed output safety, including the error-report path (audit A05)."""

import json
import os
from pathlib import Path

import pytest

from investment_terminal.cli.weekly_candle_refresh import main
from tests.test_weekly_candle_refresh import END


def arguments(tmp_path, **overrides):
    values = {
        "manifest": tmp_path / "manifest.json",
        "manifest-checksum": "a" * 64,
        "source-checkpoint-directory": tmp_path / "source",
        "weekly-checkpoint": tmp_path / "weekly.json",
        "database": tmp_path / "missing.db",
        "cache-directory": tmp_path / "cache",
        "report-output": tmp_path / "report.json",
        "end": END.isoformat(), "max-items": 1,
    }
    values.update(overrides)
    return [part for key, value in values.items() for part in ("--" + key, str(value))]


@pytest.mark.parametrize("target", ["manifest.json", "weekly.json", "missing.db",
                                    "missing.db-wal", "missing.db-shm", "missing.db-journal",
                                    "source/batch_0001.json", "cache/entry.json"])
def test_report_collision_preserves_bytes_without_invoking_writer(tmp_path, target, capsys):
    source = tmp_path / target
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"original private bytes")
    writes = []
    result = main(arguments(tmp_path, **{"report-output": source}) + ["--json"],
                  client=object(), writer=lambda *args: writes.append(args))
    assert result == 1 and writes == []
    assert source.read_bytes() == b"original private bytes"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no report written" in captured.err
    assert str(tmp_path) not in captured.err
    assert not (tmp_path / "report.json").exists()


@pytest.mark.parametrize("target", ["manifest.json", "missing.db", "missing.db-wal",
                                    "report.json", "source/batch_0001.json", "cache/entry.json"])
def test_checkpoint_collision_causes_no_writes(tmp_path, target):
    writes = []
    result = main(arguments(tmp_path, **{"weekly-checkpoint": tmp_path / target}),
                  client=object(), writer=lambda *args: writes.append(args))
    assert result == 1 and writes == []
    assert not (tmp_path / "report.json").exists()


def test_existing_report_is_not_overwritten(tmp_path):
    report = tmp_path / "report.json"
    report.write_bytes(b"previous report")
    assert main(arguments(tmp_path), client=object()) == 1
    assert report.read_bytes() == b"previous report"


@pytest.mark.parametrize("alias", ["hardlink", "relative"])
def test_file_alias_is_rejected(tmp_path, alias):
    original = tmp_path / "manifest.json"
    original.write_bytes(b"original")
    if alias == "hardlink":
        candidate = tmp_path / "alias.json"
        os.link(original, candidate)
    else:
        candidate = tmp_path / "sub" / ".." / "manifest.json"
    writes = []
    assert main(arguments(tmp_path, **{"report-output": candidate}),
                writer=lambda *args: writes.append(args)) == 1
    assert writes == [] and original.read_bytes() == b"original"


def test_uncreated_source_checkpoint_destination_is_rejected(tmp_path):
    path = tmp_path / "source" / "new.json"
    assert main(arguments(tmp_path, **{"report-output": path})) == 1
    assert not path.parent.exists()


@pytest.mark.parametrize("field,target", [
    ("cache-directory", "missing.db"),
    ("cache-directory", "source/cache"),
    ("cache-directory", "."),
    ("report-output", "source"),
])
def test_directory_collisions_fail_before_database_open(tmp_path, field, target):
    source = tmp_path / "source"
    source.mkdir()
    (tmp_path / "missing.db").write_bytes(b"not a database")
    writes = []
    assert main(arguments(tmp_path, **{field: tmp_path / target}),
                writer=lambda *args: writes.append(args)) == 1
    assert writes == []
    assert (tmp_path / "missing.db").read_bytes() == b"not a database"


def test_safe_preflight_failure_still_emits_existing_redacted_contract(tmp_path):
    assert main(arguments(tmp_path), clock=lambda: END) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["schema_version"] == 1
    assert report["status"] == "FAILED" and report["coverage"] is None
    assert report["failure"] == "PRECONDITION_OR_RUNTIME_FAILURE"
    assert str(tmp_path) not in json.dumps(report)
    assert not (tmp_path / "missing.db").exists()


def test_report_created_during_failure_is_preserved(tmp_path):
    report = tmp_path / "report.json"

    def clock():
        report.write_bytes(b"other writer")
        return END

    writes = []
    assert main(arguments(tmp_path), clock=clock,
                writer=lambda *args: writes.append(args)) == 1
    assert writes == [] and report.read_bytes() == b"other writer"


def test_writer_failure_returns_nonzero_and_redacted_error(tmp_path, capsys):
    def writer(*args):
        raise OSError("private error text")

    assert main(arguments(tmp_path), clock=lambda: END, writer=writer) == 1
    captured = capsys.readouterr()
    assert "private error text" not in captured.err
    assert "report write failed" in captured.err

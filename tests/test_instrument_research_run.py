"""The profile-backed command delegates to the established export boundary."""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.instrument_research_run import main
from tests.test_instrument_research_export import _cli_args


def _setup(tmp_path):
    export_args, private, _, projection = _cli_args(tmp_path)
    option = dict(zip(export_args[::2], export_args[1::2]))
    report_dir = tmp_path / "reports"
    checkpoint_dir = tmp_path / "weekly"
    checkpoint_dir.mkdir()
    Path(option["--weekly-checkpoint"]).replace(
        checkpoint_dir / "weekly_candle_refresh_2026-09-22.json"
    )
    profile_path = tmp_path / "profile.json"
    profile = {
        "schema_version": 1,
        "operation_identity": "WEEKLY_RUN_PROFILE",
        "manifest": option["--manifest"],
        "manifest_checksum": option["--manifest-checksum"],
        "source_checkpoint_directory": option["--source-checkpoint-directory"],
        "database": option["--database"],
        "cache_directory": str(tmp_path / "cache"),
        "weekly_checkpoint_directory": str(checkpoint_dir),
        "report_directory": str(report_dir),
    }
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    report = report_dir / "research.json"
    args = [
        "--profile", str(profile_path),
        "--projection", str(projection),
        "--projection-sha256", option["--projection-sha256"],
        "--symbol", option["--symbol"],
        "--history-start", option["--history-start"],
        "--end", option["--end"],
        "--private-output", str(private),
        "--report-output", str(report),
    ]
    return args, profile_path, profile, private, report, projection


def _replace(args, flag, value):
    changed = args.copy()
    changed[changed.index(flag) + 1] = str(value)
    return changed


def test_generic_run_exports_selected_symbol_without_database_write(tmp_path, capsys):
    args, _, profile, private, report, _ = _setup(tmp_path)
    before = Path(profile["database"]).read_bytes()
    assert main(args) == 0
    value = json.loads(private.read_text(encoding="utf-8"))
    redacted = json.loads(report.read_text(encoding="utf-8"))
    assert value["status"] == redacted["status"] == "COMPLETE"
    assert value["symbol"] == args[args.index("--symbol") + 1]
    assert value["symbol"] not in str(redacted)
    assert redacted["candle_count"] == 2
    assert Path(profile["database"]).read_bytes() == before
    output = capsys.readouterr().out
    assert f"SEND: {report}" in output
    assert str(private) not in output


@pytest.mark.parametrize("change", [
    "missing_profile", "bad_profile", "non_utc_end", "missing_projection",
    "private_in_reports", "report_outside_reports", "bad_checksum_shape",
])
def test_preflight_rejects_unsafe_or_missing_inputs_without_outputs(
        tmp_path, capsys, change):
    args, profile_path, profile, private, report, projection = _setup(tmp_path)
    if change == "missing_profile":
        args = _replace(args, "--profile", tmp_path / "missing.json")
    elif change == "bad_profile":
        profile["database"] = "relative.db"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
    elif change == "non_utc_end":
        args = _replace(args, "--end", "2026-09-22T01:00:00+01:00")
    elif change == "missing_projection":
        args = _replace(args, "--projection", tmp_path / "missing.json")
    elif change == "private_in_reports":
        args = _replace(args, "--private-output", report.parent / "private.json")
    elif change == "report_outside_reports":
        args = _replace(args, "--report-output", tmp_path / "report.json")
    else:
        args = _replace(args, "--projection-sha256", "bad")
    assert main(args) == 1
    assert not private.exists() and not report.exists()
    output = capsys.readouterr()
    assert "SEND:" not in output.out
    assert str(projection) not in output.err
    assert str(profile_path) not in output.err


def test_projection_byte_mismatch_writes_only_redacted_failure(tmp_path, capsys):
    args, _, _, private, report, projection = _setup(tmp_path)
    projection.write_text("{}", encoding="utf-8")
    assert main(args) == 1
    assert not private.exists()
    redacted = json.loads(report.read_text(encoding="utf-8"))
    assert redacted["status"] == "FAILED"
    assert redacted["failure"] == "PRECONDITION_OR_RUNTIME_FAILURE"
    assert "SEND:" in capsys.readouterr().out


def test_existing_output_is_never_overwritten(tmp_path):
    args, _, _, private, report, _ = _setup(tmp_path)
    report.parent.mkdir()
    report.write_bytes(b"existing")
    assert main(args) == 1
    assert report.read_bytes() == b"existing"
    assert not private.exists()

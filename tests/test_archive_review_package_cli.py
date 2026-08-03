"""
Tests for the historical snapshot archive CLI.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.cli.archive_review_package import (
    main,
)


def write_package(
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "generated_at": (
                    "2026-08-03T17:35:00+00:00"
                ),
                "portfolio_name": "Test Portfolio",
                "warnings": [],
                "sections": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_cli_archives_review_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = (
        tmp_path
        / "output"
        / "investment_review_package.json"
    )
    history_root = (
        tmp_path
        / "history"
    )
    write_package(
        package
    )

    main(
        [
            "--review-package",
            str(package),
            "--history-root",
            str(history_root),
            "--package-id",
            "review-001",
            "--product-version",
            "0.12.0",
        ]
    )

    output = capsys.readouterr().out

    assert "Historical snapshot archived" in output
    assert "Snapshot ID" in output
    assert "Archive file" in output
    assert (
        history_root
        / "manifest.jsonl"
    ).exists()

    archived_files = tuple(
        history_root.rglob(
            "*.json"
        )
    )

    assert len(
        archived_files
    ) == 1


def test_cli_prints_json_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = tmp_path / "review.json"
    history_root = tmp_path / "history"
    write_package(
        package
    )

    main(
        [
            "--review-package",
            str(package),
            "--history-root",
            str(history_root),
            "--json",
        ]
    )

    payload = json.loads(
        capsys.readouterr().out
    )

    assert payload[
        "package_schema_version"
    ] == "1.0"
    assert payload[
        "status"
    ] == "ARCHIVED"
    assert payload[
        "relative_path"
    ].endswith(
        ".json"
    )


def test_cli_supports_custom_manifest(
    tmp_path: Path,
) -> None:
    package = tmp_path / "review.json"
    history_root = tmp_path / "history"
    manifest = (
        tmp_path
        / "indexes"
        / "snapshots.jsonl"
    )
    write_package(
        package
    )

    main(
        [
            "--review-package",
            str(package),
            "--history-root",
            str(history_root),
            "--manifest",
            str(manifest),
        ]
    )

    assert manifest.exists()


def test_cli_reports_missing_package(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--review-package",
                str(
                    tmp_path
                    / "missing.json"
                ),
                "--history-root",
                str(
                    tmp_path
                    / "history"
                ),
            ]
        )

    assert exc.value.code == 2
    assert (
        "Review package does not exist"
        in capsys.readouterr().err
    )


def test_cli_reports_invalid_supersedes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = tmp_path / "review.json"
    write_package(
        package
    )

    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--review-package",
                str(package),
                "--history-root",
                str(
                    tmp_path
                    / "history"
                ),
                "--supersedes",
                "not-a-uuid",
            ]
        )

    assert exc.value.code == 2
    assert (
        "supersedes must be a valid UUID string"
        in capsys.readouterr().err
    )


def test_cli_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(
        SystemExit,
    ) as exc:
        main(
            [
                "--help",
            ]
        )

    assert exc.value.code == 0
    assert (
        "Archive one investment review package"
        in capsys.readouterr().out
    )

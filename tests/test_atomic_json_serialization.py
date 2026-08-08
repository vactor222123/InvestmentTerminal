"""
Tests for centralized atomic JSON serialization.
"""

import json
from pathlib import Path

import pytest

from investment_terminal.utils.atomic_write import (
    write_json_atomic,
)


def test_write_json_atomic_can_preserve_unicode(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "unicode.json"

    write_json_atomic(
        destination,
        {
            "city": "München",
            "label": "Київ",
        },
        ensure_ascii=False,
    )

    text = destination.read_text(
        encoding="utf-8"
    )

    assert "München" in text
    assert "Київ" in text
    assert json.loads(text) == {
        "city": "München",
        "label": "Київ",
    }


def test_write_json_atomic_can_disable_trailing_newline(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "compact.json"

    write_json_atomic(
        destination,
        {
            "value": 1,
        },
        trailing_newline=False,
    )

    assert not destination.read_text(
        encoding="utf-8"
    ).endswith("\n")


def test_write_json_atomic_rejects_invalid_ensure_ascii(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TypeError,
        match="ensure_ascii must be a bool",
    ):
        write_json_atomic(
            tmp_path / "payload.json",
            {
                "value": 1,
            },
            ensure_ascii="no",  # type: ignore[arg-type]
        )


def test_write_json_atomic_preserves_existing_file_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "payload.json"
    original = '{"state":"previous"}'
    destination.write_text(
        original,
        encoding="utf-8",
    )

    def fail_replace(
        source: object,
        target: object,
    ) -> None:
        raise OSError(
            "replace failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        fail_replace,
    )

    with pytest.raises(
        OSError,
        match="replace failed",
    ):
        write_json_atomic(
            destination,
            {
                "state": "new",
            },
            ensure_ascii=False,
        )

    assert destination.read_text(
        encoding="utf-8"
    ) == original
    assert list(
        tmp_path.glob(
            ".payload.json.*.tmp"
        )
    ) == []

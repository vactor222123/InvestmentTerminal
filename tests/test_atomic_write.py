"""
Tests for atomic filesystem write helpers.
"""

import json
import os
import stat
from pathlib import Path

import pytest

from investment_terminal.utils.atomic_write import (
    write_bytes_atomic,
    write_json_atomic,
    write_text_atomic,
)


def test_write_bytes_atomic_creates_file(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "data.bin"

    result = write_bytes_atomic(
        destination,
        b"payload",
    )

    assert result == destination
    assert destination.read_bytes() == b"payload"


def test_write_text_atomic_creates_parent_directories(
    tmp_path: Path,
) -> None:
    destination = (
        tmp_path
        / "nested"
        / "document.txt"
    )

    write_text_atomic(
        destination,
        "hello",
    )

    assert destination.read_text(
        encoding="utf-8"
    ) == "hello"


def test_write_text_atomic_replaces_existing_file(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "document.txt"
    destination.write_text(
        "old",
        encoding="utf-8",
    )

    write_text_atomic(
        destination,
        "new",
    )

    assert destination.read_text(
        encoding="utf-8"
    ) == "new"


def test_write_text_atomic_preserves_existing_file_mode(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "document.txt"
    destination.write_text(
        "old",
        encoding="utf-8",
    )
    os.chmod(
        destination,
        0o640,
    )
    expected_mode = stat.S_IMODE(
        destination.stat().st_mode
    )

    write_text_atomic(
        destination,
        "new",
    )

    assert stat.S_IMODE(
        destination.stat().st_mode
    ) == expected_mode


def test_write_text_atomic_syncs_parent_after_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"
    calls: list[Path] = []

    def record_sync(
        directory: Path,
    ) -> None:
        calls.append(
            directory
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write."
        "_sync_parent_directory",
        record_sync,
    )

    write_text_atomic(
        destination,
        "content",
    )

    assert calls == [
        tmp_path,
    ]


def test_parent_sync_happens_after_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"
    events: list[str] = []
    real_replace = os.replace

    def record_replace(
        source: object,
        target: object,
    ) -> None:
        events.append(
            "replace"
        )
        real_replace(
            source,
            target,
        )

    def record_sync(
        directory: Path,
    ) -> None:
        events.append(
            "sync"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        record_replace,
    )
    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write."
        "_sync_parent_directory",
        record_sync,
    )

    write_text_atomic(
        destination,
        "content",
    )

    assert events == [
        "replace",
        "sync",
    ]


def test_parent_sync_failure_reports_durability_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"

    def fail_sync(
        directory: Path,
    ) -> None:
        raise OSError(
            "directory sync failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write."
        "_sync_parent_directory",
        fail_sync,
    )

    with pytest.raises(
        OSError,
        match="directory sync failed",
    ):
        write_text_atomic(
            destination,
            "content",
        )

    assert destination.read_text(
        encoding="utf-8"
    ) == "content"
    assert list(
        tmp_path.glob(
            ".document.txt.*.tmp"
        )
    ) == []


def test_write_text_atomic_preserves_unicode(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "unicode.txt"

    write_text_atomic(
        destination,
        "Київ — München",
    )

    assert destination.read_text(
        encoding="utf-8"
    ) == "Київ — München"


def test_write_json_atomic_writes_valid_pretty_json(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "payload.json"

    write_json_atomic(
        destination,
        {
            "symbol": "VWCE",
            "score": 88,
        },
    )

    text = destination.read_text(
        encoding="utf-8"
    )

    assert text.endswith("\n")
    assert json.loads(text) == {
        "symbol": "VWCE",
        "score": 88,
    }
    assert "\n  \"symbol\"" in text


def test_write_json_atomic_can_sort_keys(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "payload.json"

    write_json_atomic(
        destination,
        {
            "z": 1,
            "a": 2,
        },
        sort_keys=True,
    )

    text = destination.read_text(
        encoding="utf-8"
    )

    assert text.index('"a"') < text.index('"z"')


def test_write_json_atomic_rejects_nan(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "payload.json"

    with pytest.raises(
        ValueError,
    ):
        write_json_atomic(
            destination,
            {
                "score": float("nan"),
            },
        )

    assert not destination.exists()


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
    ],
)
def test_write_text_atomic_rejects_empty_path(
    value: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="path must be a non-empty path",
    ):
        write_text_atomic(
            value,
            "content",
        )


def test_failed_replace_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"

    def fail_replace(
        source: object,
        target: object,
    ) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        fail_replace,
    )

    with pytest.raises(
        OSError,
        match="replace failed",
    ):
        write_text_atomic(
            destination,
            "content",
        )

    assert not destination.exists()
    assert list(
        tmp_path.glob(
            ".document.txt.*.tmp"
        )
    ) == []


def test_failed_replace_preserves_existing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"
    destination.write_text(
        "original",
        encoding="utf-8",
    )

    def fail_replace(
        source: object,
        target: object,
    ) -> None:
        raise PermissionError(
            "destination is locked"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        fail_replace,
    )

    with pytest.raises(
        PermissionError,
        match="destination is locked",
    ):
        write_text_atomic(
            destination,
            "replacement",
        )

    assert destination.read_text(
        encoding="utf-8"
    ) == "original"
    assert list(
        tmp_path.glob(
            ".document.txt.*.tmp"
        )
    ) == []


def test_failed_fsync_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"

    def fail_fsync(
        file_descriptor: int,
    ) -> None:
        raise OSError(
            "disk sync failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.fsync",
        fail_fsync,
    )

    with pytest.raises(
        OSError,
        match="disk sync failed",
    ):
        write_text_atomic(
            destination,
            "content",
        )

    assert not destination.exists()
    assert list(
        tmp_path.glob(
            ".document.txt.*.tmp"
        )
    ) == []


def test_failed_permission_copy_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"
    destination.write_text(
        "original",
        encoding="utf-8",
    )

    def fail_chmod(
        path: object,
        mode: int,
    ) -> None:
        raise PermissionError(
            "chmod failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.chmod",
        fail_chmod,
    )

    with pytest.raises(
        PermissionError,
        match="chmod failed",
    ):
        write_text_atomic(
            destination,
            "replacement",
        )

    assert destination.read_text(
        encoding="utf-8"
    ) == "original"
    assert list(
        tmp_path.glob(
            ".document.txt.*.tmp"
        )
    ) == []


def test_cleanup_failure_does_not_mask_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "document.txt"

    def fail_replace(
        source: object,
        target: object,
    ) -> None:
        raise OSError(
            "replace failed"
        )

    def fail_unlink(
        self: Path,
        missing_ok: bool = False,
    ) -> None:
        raise PermissionError(
            "cleanup failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        fail_replace,
    )
    monkeypatch.setattr(
        Path,
        "unlink",
        fail_unlink,
    )

    with pytest.raises(
        OSError,
        match="replace failed",
    ):
        write_text_atomic(
            destination,
            "content",
        )

    assert not destination.exists()

"""
Atomic filesystem write helpers.

Mutable files are written to a temporary file in the destination directory,
flushed to disk, and then replaced atomically.
"""

from __future__ import annotations

import errno
import json
import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


_UNSUPPORTED_DIRECTORY_SYNC_ERRNOS = frozenset(
    code
    for code in (
        errno.EINVAL,
        getattr(
            errno,
            "ENOTSUP",
            None,
        ),
        getattr(
            errno,
            "EOPNOTSUPP",
            None,
        ),
    )
    if code is not None
)


def write_bytes_atomic(
    path: str | Path,
    data: bytes,
) -> Path:
    """Atomically write bytes to a destination path."""
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    destination = _normalize_path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path: Path | None = None
    destination_mode = _existing_file_mode(
        destination
    )

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(data)
            temporary.flush()

            if destination_mode is not None:
                os.chmod(
                    temporary_path,
                    destination_mode,
                )

            os.fsync(
                temporary.fileno()
            )

        os.replace(
            temporary_path,
            destination,
        )
        temporary_path = None

        _sync_parent_directory(
            destination.parent
        )
    except BaseException:
        _remove_temporary_file(
            temporary_path
        )
        raise

    return destination


def write_text_atomic(
    path: str | Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    """Atomically write text using the requested encoding."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if (
        not isinstance(encoding, str)
        or not encoding.strip()
    ):
        raise ValueError(
            "encoding must be a non-empty string"
        )

    return write_bytes_atomic(
        path,
        text.encode(encoding),
    )


def write_json_atomic(
    path: str | Path,
    payload: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = True,
    trailing_newline: bool = True,
) -> Path:
    """Serialize and atomically write a JSON document."""
    if not isinstance(
        ensure_ascii,
        bool,
    ):
        raise TypeError(
            "ensure_ascii must be a bool"
        )

    text = json.dumps(
        payload,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=ensure_ascii,
        allow_nan=False,
    )

    if trailing_newline:
        text += "\n"

    return write_text_atomic(
        path,
        text,
        encoding="utf-8",
    )


def sync_directory(
    directory: str | Path,
) -> None:
    """
    Persist directory-entry changes when the platform/filesystem supports it.

    Unsupported directory synchronization is tolerated. Other I/O failures
    remain visible to the caller.
    """
    normalized = (
        directory
        if isinstance(directory, Path)
        else Path(directory)
    )
    _sync_parent_directory(
        normalized
    )


def _normalize_path(
    path: str | Path,
) -> Path:
    if isinstance(path, Path):
        destination = path
    elif isinstance(path, str):
        if not path.strip():
            raise ValueError(
                "path must be a non-empty path"
            )
        destination = Path(path)
    else:
        raise TypeError(
            "path must be a string or Path"
        )

    if not destination.name:
        raise ValueError(
            "path must identify a file"
        )

    return destination


def _existing_file_mode(
    destination: Path,
) -> int | None:
    try:
        current_mode = destination.stat().st_mode
    except FileNotFoundError:
        return None

    return stat.S_IMODE(
        current_mode
    )


def _sync_parent_directory(
    directory: Path,
) -> None:
    """
    Persist a directory entry when supported.

    Windows does not provide a portable directory fsync through os.open,
    so the file-level fsync remains the strongest portable guarantee there.
    Filesystems that explicitly report directory synchronization as
    unsupported are tolerated; other I/O failures remain visible.
    """
    if os.name == "nt":
        return

    flags = os.O_RDONLY

    if hasattr(
        os,
        "O_DIRECTORY",
    ):
        flags |= os.O_DIRECTORY

    try:
        directory_fd = os.open(
            directory,
            flags,
        )
    except OSError as exc:
        if _is_unsupported_directory_sync_error(
            exc
        ):
            return
        raise

    try:
        try:
            os.fsync(
                directory_fd
            )
        except OSError as exc:
            if not _is_unsupported_directory_sync_error(
                exc
            ):
                raise
    finally:
        os.close(
            directory_fd
        )


def _is_unsupported_directory_sync_error(
    exc: OSError,
) -> bool:
    return (
        exc.errno
        in _UNSUPPORTED_DIRECTORY_SYNC_ERRNOS
    )


def _remove_temporary_file(
    temporary_path: Path | None,
) -> None:
    if temporary_path is None:
        return

    with suppress(
        OSError,
    ):
        temporary_path.unlink()

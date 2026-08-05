"""
Atomic filesystem write helpers.

Mutable files are written to a temporary file in the destination directory,
flushed to disk, and then replaced atomically.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


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
            os.fsync(temporary.fileno())

        os.replace(
            temporary_path,
            destination,
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
    trailing_newline: bool = True,
) -> Path:
    """Serialize and atomically write a JSON document."""
    text = json.dumps(
        payload,
        indent=indent,
        sort_keys=sort_keys,
        allow_nan=False,
    )

    if trailing_newline:
        text += "\n"

    return write_text_atomic(
        path,
        text,
        encoding="utf-8",
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


def _remove_temporary_file(
    temporary_path: Path | None,
) -> None:
    if temporary_path is None:
        return

    with suppress(
        OSError,
    ):
        temporary_path.unlink()

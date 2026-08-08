"""
Architecture guard for JSON persistence boundaries.

Persistent JSON artifacts must use the shared atomic writer. This protects
already-hardened exporters and portfolio writers from regressing to direct
filesystem writes.
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JSON_PERSISTENCE_MODULES = (
    Path(
        "investment_terminal/exporters/"
        "analysis_exporter.py"
    ),
    Path(
        "investment_terminal/exporters/"
        "portfolio_exporter.py"
    ),
    Path(
        "investment_terminal/review/"
        "review_package_exporter.py"
    ),
    Path(
        "investment_terminal/portfolio/"
        "current_portfolio_writer.py"
    ),
    Path(
        "investment_terminal/cli/"
        "investment_review_package.py"
    ),
)


def test_json_persistence_uses_shared_atomic_writer() -> None:
    violations: list[str] = []

    for relative_path in JSON_PERSISTENCE_MODULES:
        module_path = PROJECT_ROOT / relative_path
        tree = ast.parse(
            module_path.read_text(
                encoding="utf-8"
            ),
            filename=str(module_path),
        )

        if not _imports_atomic_json_writer(
            tree
        ):
            violations.append(
                f"{relative_path} does not import "
                "write_json_atomic"
            )

        if not _calls_atomic_json_writer(
            tree
        ):
            violations.append(
                f"{relative_path} does not call "
                "write_json_atomic"
            )

        violations.extend(
            _find_direct_write_violations(
                tree,
                relative_path=relative_path,
            )
        )

    assert violations == [], (
        "Persistent JSON artifacts must use "
        "investment_terminal.utils.atomic_write."
        "write_json_atomic:\n"
        + "\n".join(
            violations
        )
    )


def _imports_atomic_json_writer(
    tree: ast.AST,
) -> bool:
    for node in ast.walk(
        tree
    ):
        if not isinstance(
            node,
            ast.ImportFrom,
        ):
            continue

        if (
            node.module
            != "investment_terminal.utils.atomic_write"
        ):
            continue

        if any(
            alias.name == "write_json_atomic"
            for alias in node.names
        ):
            return True

    return False


def _calls_atomic_json_writer(
    tree: ast.AST,
) -> bool:
    return any(
        isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == "write_json_atomic"
        for node in ast.walk(
            tree
        )
    )


def _find_direct_write_violations(
    tree: ast.AST,
    *,
    relative_path: Path,
) -> list[str]:
    violations: list[str] = []

    for node in ast.walk(
        tree
    ):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if _is_json_dump_call(
            node
        ):
            violations.append(
                f"{relative_path}:{node.lineno} "
                "uses json.dump"
            )
            continue

        if _is_direct_path_write_call(
            node
        ):
            violations.append(
                f"{relative_path}:{node.lineno} "
                "uses direct Path write"
            )
            continue

        if _is_direct_write_mode_open(
            node
        ):
            violations.append(
                f"{relative_path}:{node.lineno} "
                "opens a file directly for writing"
            )

    return violations


def _is_json_dump_call(
    node: ast.Call,
) -> bool:
    return (
        isinstance(
            node.func,
            ast.Attribute,
        )
        and isinstance(
            node.func.value,
            ast.Name,
        )
        and node.func.value.id == "json"
        and node.func.attr == "dump"
    )


def _is_direct_path_write_call(
    node: ast.Call,
) -> bool:
    return (
        isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr
        in {
            "write_text",
            "write_bytes",
        }
    )


def _is_direct_write_mode_open(
    node: ast.Call,
) -> bool:
    if not (
        isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == "open"
    ):
        return False

    mode = _open_mode(
        node
    )

    return (
        mode is not None
        and any(
            flag in mode
            for flag in (
                "w",
                "a",
                "x",
                "+",
            )
        )
    )


def _open_mode(
    node: ast.Call,
) -> str | None:
    if node.args:
        first_argument = node.args[0]

        if (
            isinstance(
                first_argument,
                ast.Constant,
            )
            and isinstance(
                first_argument.value,
                str,
            )
        ):
            return first_argument.value

    for keyword in node.keywords:
        if keyword.arg != "mode":
            continue

        if (
            isinstance(
                keyword.value,
                ast.Constant,
            )
            and isinstance(
                keyword.value.value,
                str,
            )
        ):
            return keyword.value.value

    return "r"

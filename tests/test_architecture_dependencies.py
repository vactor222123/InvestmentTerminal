"""
Architecture tests protecting the CLI composition boundary.
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "investment_terminal"
CLI_PACKAGE = PACKAGE_ROOT / "cli"


def test_non_cli_modules_do_not_import_cli_package() -> None:
    violations: list[str] = []

    for module_path in sorted(
        PACKAGE_ROOT.rglob("*.py")
    ):
        if _is_inside(
            module_path,
            CLI_PACKAGE,
        ):
            continue

        source = module_path.read_text(
            encoding="utf-8"
        )
        tree = ast.parse(
            source,
            filename=str(module_path),
        )

        for node in ast.walk(
            tree
        ):
            imported_names = _imported_names(
                node
            )

            for imported_name in imported_names:
                if (
                    imported_name
                    == "investment_terminal.cli"
                    or imported_name.startswith(
                        "investment_terminal.cli."
                    )
                ):
                    relative_path = module_path.relative_to(
                        PROJECT_ROOT
                    )
                    violations.append(
                        f"{relative_path}:{node.lineno} "
                        f"imports {imported_name}"
                    )

    assert violations == [], (
        "The CLI is a composition boundary and must not be "
        "imported by domain or infrastructure modules:\n"
        + "\n".join(
            violations
        )
    )


def _imported_names(
    node: ast.AST,
) -> tuple[str, ...]:
    if isinstance(
        node,
        ast.Import,
    ):
        return tuple(
            alias.name
            for alias in node.names
        )

    if isinstance(
        node,
        ast.ImportFrom,
    ):
        module_name = node.module

        if module_name is None:
            return ()

        return (
            module_name,
        )

    return ()


def _is_inside(
    path: Path,
    directory: Path,
) -> bool:
    try:
        path.relative_to(
            directory
        )
    except ValueError:
        return False

    return True

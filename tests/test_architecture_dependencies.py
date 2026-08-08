"""
Architecture tests protecting dependency boundaries.
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "investment_terminal"
CLI_PACKAGE = PACKAGE_ROOT / "cli"
HISTORY_PACKAGE = PACKAGE_ROOT / "history"
REVIEW_PACKAGE = PACKAGE_ROOT / "review"


def test_non_cli_modules_do_not_import_cli_package() -> None:
    violations = _find_forbidden_imports(
        forbidden_package="investment_terminal.cli",
        excluded_directories=(
            CLI_PACKAGE,
        ),
    )

    assert violations == [], (
        "The CLI is a composition boundary and must not be "
        "imported by domain or infrastructure modules:\n"
        + "\n".join(
            violations
        )
    )


def test_non_history_modules_do_not_import_history_package() -> None:
    violations = _find_forbidden_imports(
        forbidden_package="investment_terminal.history",
        excluded_directories=(
            CLI_PACKAGE,
            HISTORY_PACKAGE,
        ),
    )

    assert violations == [], (
        "History is a downstream evidence and query boundary. "
        "Only History itself and the CLI composition layer may "
        "import it:\n"
        + "\n".join(
            violations
        )
    )


def test_upstream_modules_do_not_import_review_package() -> None:
    violations = _find_forbidden_imports(
        forbidden_package="investment_terminal.review",
        excluded_directories=(
            CLI_PACKAGE,
            HISTORY_PACKAGE,
            REVIEW_PACKAGE,
        ),
    )

    assert violations == [], (
        "Review is a downstream assembly boundary. Upstream "
        "domains must produce their own outputs without importing "
        "Review:\n"
        + "\n".join(
            violations
        )
    )


def test_relative_from_import_resolves_imported_alias() -> None:
    tree = ast.parse(
        "from .. import history\n"
    )
    node = tree.body[0]

    assert isinstance(
        node,
        ast.ImportFrom,
    )
    assert _imported_names(
        node,
        module_path=(
            PACKAGE_ROOT
            / "portfolio"
            / "module.py"
        ),
    ) == (
        "investment_terminal",
        "investment_terminal.history",
    )


def test_relative_from_import_resolves_explicit_module() -> None:
    tree = ast.parse(
        "from ..history import repository\n"
    )
    node = tree.body[0]

    assert isinstance(
        node,
        ast.ImportFrom,
    )
    assert _imported_names(
        node,
        module_path=(
            PACKAGE_ROOT
            / "portfolio"
            / "module.py"
        ),
    ) == (
        "investment_terminal.history",
        "investment_terminal.history.repository",
    )


def test_absolute_from_import_resolves_imported_alias() -> None:
    tree = ast.parse(
        "from investment_terminal import history\n"
    )
    node = tree.body[0]

    assert isinstance(
        node,
        ast.ImportFrom,
    )
    assert _imported_names(
        node,
        module_path=(
            PACKAGE_ROOT
            / "portfolio"
            / "module.py"
        ),
    ) == (
        "investment_terminal",
        "investment_terminal.history",
    )


def test_absolute_from_import_resolves_explicit_module() -> None:
    tree = ast.parse(
        "from investment_terminal.history import repository\n"
    )
    node = tree.body[0]

    assert isinstance(
        node,
        ast.ImportFrom,
    )
    assert _imported_names(
        node,
        module_path=(
            PACKAGE_ROOT
            / "portfolio"
            / "module.py"
        ),
    ) == (
        "investment_terminal.history",
        "investment_terminal.history.repository",
    )


def _find_forbidden_imports(
    *,
    forbidden_package: str,
    excluded_directories: tuple[Path, ...],
) -> list[str]:
    violations: list[str] = []

    for module_path in sorted(
        PACKAGE_ROOT.rglob("*.py")
    ):
        if any(
            _is_inside(
                module_path,
                directory,
            )
            for directory in excluded_directories
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
            for imported_name in _imported_names(
                node,
                module_path=module_path,
            ):
                if (
                    imported_name
                    == forbidden_package
                    or imported_name.startswith(
                        f"{forbidden_package}."
                    )
                ):
                    relative_path = module_path.relative_to(
                        PROJECT_ROOT
                    )
                    violations.append(
                        f"{relative_path}:{node.lineno} "
                        f"imports {imported_name}"
                    )

    return violations


def _imported_names(
    node: ast.AST,
    *,
    module_path: Path,
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
        base_package = _resolve_import_from(
            node,
            module_path=module_path,
        )

        if base_package is None:
            return ()

        names = [
            base_package,
        ]

        names.extend(
            f"{base_package}.{alias.name}"
            for alias in node.names
            if alias.name != "*"
        )

        return tuple(
            names
        )

    return ()


def _resolve_import_from(
    node: ast.ImportFrom,
    *,
    module_path: Path,
) -> str | None:
    if node.level == 0:
        return node.module

    relative_module = module_path.relative_to(
        PROJECT_ROOT
    ).with_suffix("")
    package_parts = list(
        relative_module.parts[:-1]
    )
    parent_count = node.level - 1

    if parent_count > len(
        package_parts
    ):
        return None

    base_parts = (
        package_parts[
            : len(package_parts) - parent_count
        ]
        if parent_count
        else package_parts
    )
    imported_parts = (
        node.module.split(".")
        if node.module
        else []
    )
    absolute_parts = [
        *base_parts,
        *imported_parts,
    ]

    if not absolute_parts:
        return None

    return ".".join(
        absolute_parts
    )


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

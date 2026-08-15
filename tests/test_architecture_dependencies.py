"""
Architecture tests protecting dependency and authority boundaries.
"""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "investment_terminal"
CLI_PACKAGE = PACKAGE_ROOT / "cli"
HISTORY_PACKAGE = PACKAGE_ROOT / "history"
REVIEW_PACKAGE = PACKAGE_ROOT / "review"
KNOWLEDGE_PACKAGE = PACKAGE_ROOT / "knowledge"
AI_PACKAGE = PACKAGE_ROOT / "ai"
APPLICATION_PACKAGE = PACKAGE_ROOT / "application"
API_PACKAGE = PACKAGE_ROOT / "api"
SERVER_PACKAGE = PACKAGE_ROOT / "server"


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


def test_history_does_not_depend_on_downstream_interpretation_or_transport() -> None:
    violations = _find_forbidden_imports_from(
        source_directories=(
            HISTORY_PACKAGE,
        ),
        forbidden_packages=(
            "investment_terminal.knowledge",
            "investment_terminal.ai",
            "investment_terminal.application",
            "investment_terminal.api",
            "investment_terminal.server",
        ),
    )

    assert violations == [], (
        "History is canonical historical evidence and must not "
        "depend on downstream Knowledge, AI, application, API, or "
        "server layers:\n"
        + "\n".join(
            violations
        )
    )


def test_knowledge_does_not_depend_on_ai_application_or_transport() -> None:
    violations = _find_forbidden_imports_from(
        source_directories=(
            KNOWLEDGE_PACKAGE,
        ),
        forbidden_packages=(
            "investment_terminal.ai",
            "investment_terminal.application",
            "investment_terminal.api",
            "investment_terminal.server",
        ),
    )

    assert violations == [], (
        "Knowledge is upstream authority for grounded AI and must "
        "not depend on AI orchestration or transport layers:\n"
        + "\n".join(
            violations
        )
    )


def test_ai_does_not_depend_back_on_history_review_or_outer_layers() -> None:
    violations = _find_forbidden_imports_from(
        source_directories=(
            AI_PACKAGE,
        ),
        forbidden_packages=(
            "investment_terminal.history",
            "investment_terminal.review",
            "investment_terminal.application",
            "investment_terminal.api",
            "investment_terminal.server",
            "investment_terminal.cli",
        ),
    )

    assert violations == [], (
        "Grounded AI may consume Knowledge contracts, but it must "
        "not reach backwards into History/Review or outwards into "
        "application/transport/composition layers:\n"
        + "\n".join(
            violations
        )
    )


def test_application_does_not_depend_on_server_cli_or_history_internals() -> None:
    violations = _find_forbidden_imports_from(
        source_directories=(
            APPLICATION_PACKAGE,
        ),
        forbidden_packages=(
            "investment_terminal.server",
            "investment_terminal.cli",
            "investment_terminal.history",
        ),
    )

    assert violations == [], (
        "Application services orchestrate domain boundaries and "
        "must not depend on server/CLI transports or History "
        "internals:\n"
        + "\n".join(
            violations
        )
    )


def test_api_adapter_does_not_depend_on_server_or_history_internals() -> None:
    violations = _find_forbidden_imports_from(
        source_directories=(
            API_PACKAGE,
        ),
        forbidden_packages=(
            "investment_terminal.server",
            "investment_terminal.history",
            "investment_terminal.cli",
        ),
    )

    assert violations == [], (
        "The framework-neutral API adapter must stay upstream of "
        "the production server and outside History internals:\n"
        + "\n".join(
            violations
        )
    )


def test_server_does_not_reach_into_history_internals() -> None:
    violations = _find_forbidden_imports_from(
        source_directories=(
            SERVER_PACKAGE,
        ),
        forbidden_packages=(
            "investment_terminal.history",
        ),
    )

    assert violations == [], (
        "The production server may compose application/AI/Knowledge "
        "dependencies, but it must not bypass those boundaries to "
        "reach History internals:\n"
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


def test_scoped_guard_reports_only_requested_source_directory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    other = tmp_path / "other"
    source.mkdir()
    other.mkdir()

    (source / "bad.py").write_text(
        "import investment_terminal.server\n",
        encoding="utf-8",
    )
    (other / "ignored.py").write_text(
        "import investment_terminal.server\n",
        encoding="utf-8",
    )

    violations = _find_forbidden_imports_from(
        source_directories=(
            source,
        ),
        forbidden_packages=(
            "investment_terminal.server",
        ),
    )

    assert len(violations) == 1
    assert "bad.py" in violations[0]
    assert "ignored.py" not in violations[0]


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

        violations.extend(
            _module_forbidden_imports(
                module_path=module_path,
                forbidden_packages=(
                    forbidden_package,
                ),
            )
        )

    return violations


def _find_forbidden_imports_from(
    *,
    source_directories: tuple[Path, ...],
    forbidden_packages: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []

    module_paths = {
        module_path
        for directory in source_directories
        if directory.exists()
        for module_path in directory.rglob("*.py")
    }

    for module_path in sorted(
        module_paths
    ):
        violations.extend(
            _module_forbidden_imports(
                module_path=module_path,
                forbidden_packages=forbidden_packages,
            )
        )

    return violations


def _module_forbidden_imports(
    *,
    module_path: Path,
    forbidden_packages: tuple[str, ...],
) -> list[str]:
    source = module_path.read_text(
        encoding="utf-8"
    )
    tree = ast.parse(
        source,
        filename=str(module_path),
    )
    violations: list[str] = []

    for node in ast.walk(
        tree
    ):
        for imported_name in _imported_names(
            node,
            module_path=module_path,
        ):
            for forbidden_package in forbidden_packages:
                if (
                    imported_name
                    == forbidden_package
                    or imported_name.startswith(
                        f"{forbidden_package}."
                    )
                ):
                    try:
                        display_path = module_path.relative_to(
                            PROJECT_ROOT
                        )
                    except ValueError:
                        display_path = module_path

                    violations.append(
                        f"{display_path}:{node.lineno} "
                        f"imports {imported_name}"
                    )
                    break

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

    try:
        relative_module = module_path.relative_to(
            PROJECT_ROOT
        ).with_suffix("")
    except ValueError:
        return node.module

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
            directory,
        )
    except ValueError:
        return False

    return True

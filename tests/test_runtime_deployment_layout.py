from pathlib import Path

import pytest

from investment_terminal.server.runtime_config import (
    DATABASE_ENV,
    GROUNDED_GENERATION_DATABASE_ENV,
    RUNTIME_DATA_ROOT_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
)
from investment_terminal.server.runtime_deployment_layout import (
    GroundedAIServerDeploymentLayout,
)


def layout(
    tmp_path: Path,
) -> GroundedAIServerDeploymentLayout:
    return GroundedAIServerDeploymentLayout(
        application_root=tmp_path / "app",
        runtime_data_root=tmp_path / "runtime",
        backup_root=tmp_path / "backups",
        config_root=tmp_path / "config",
        secrets_root=tmp_path / "secrets",
    )


def test_layout_projects_canonical_runtime_database_paths(
    tmp_path: Path,
) -> None:
    value = layout(
        tmp_path
    )

    assert value.knowledge_database == (
        tmp_path / "runtime" / "knowledge.db"
    ).resolve()
    assert value.usage_cost_ledger_database == (
        tmp_path
        / "runtime"
        / "operational"
        / "provider_usage_cost.db"
    ).resolve()
    assert value.grounded_generation_database == (
        tmp_path
        / "runtime"
        / "operational"
        / "grounded_generations.db"
    ).resolve()


def test_layout_projects_only_non_secret_runtime_path_environment(
    tmp_path: Path,
) -> None:
    value = layout(
        tmp_path
    )

    assert value.runtime_environment() == {
        RUNTIME_DATA_ROOT_ENV: str(
            value.runtime_data_root
        ),
        DATABASE_ENV: str(
            value.knowledge_database
        ),
        USAGE_COST_LEDGER_DATABASE_ENV: str(
            value.usage_cost_ledger_database
        ),
        GROUNDED_GENERATION_DATABASE_ENV: str(
            value.grounded_generation_database
        ),
    }
    assert all(
        "KEY" not in name
        and "SECRET" not in name
        for name in value.runtime_environment()
    )


def test_layout_is_descriptive_and_does_not_create_directories(
    tmp_path: Path,
) -> None:
    value = layout(
        tmp_path
    )

    assert not value.application_root.exists()
    assert not value.runtime_data_root.exists()
    assert not value.backup_root.exists()
    assert not value.config_root.exists()
    assert not value.secrets_root.exists()


@pytest.mark.parametrize(
    "field_name",
    (
        "application_root",
        "runtime_data_root",
        "backup_root",
        "config_root",
        "secrets_root",
    ),
)
def test_layout_requires_absolute_roots(
    tmp_path: Path,
    field_name: str,
) -> None:
    values = {
        "application_root": tmp_path / "app",
        "runtime_data_root": tmp_path / "runtime",
        "backup_root": tmp_path / "backups",
        "config_root": tmp_path / "config",
        "secrets_root": tmp_path / "secrets",
    }
    values[field_name] = Path(
        "relative"
    )

    with pytest.raises(
        ValueError,
        match=f"{field_name} must be an absolute path",
    ):
        GroundedAIServerDeploymentLayout(
            **values
        )


def test_backup_root_must_not_live_inside_runtime_data_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "runtime_data_root and backup_root "
            "must be independent deployment roots"
        ),
    ):
        GroundedAIServerDeploymentLayout(
            application_root=tmp_path / "app",
            runtime_data_root=tmp_path / "runtime",
            backup_root=(
                tmp_path
                / "runtime"
                / "backups"
            ),
            config_root=tmp_path / "config",
            secrets_root=tmp_path / "secrets",
        )


def test_runtime_root_must_not_live_inside_application_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "application_root and runtime_data_root "
            "must be independent deployment roots"
        ),
    ):
        GroundedAIServerDeploymentLayout(
            application_root=tmp_path / "deployment",
            runtime_data_root=(
                tmp_path
                / "deployment"
                / "runtime"
            ),
            backup_root=tmp_path / "backups",
            config_root=tmp_path / "config",
            secrets_root=tmp_path / "secrets",
        )

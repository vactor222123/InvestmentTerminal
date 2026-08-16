"""Canonical production deployment filesystem layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from investment_terminal.server.runtime_config import (
    DATABASE_ENV,
    GROUNDED_GENERATION_DATABASE_ENV,
    RUNTIME_DATA_ROOT_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
)


@dataclass(frozen=True, slots=True)
class GroundedAIServerDeploymentLayout:
    """
    Describe one explicit production filesystem topology.

    This object does not create directories, move databases, read secrets, or
    mutate the environment. It is a deployment contract consumed by operators
    and later container/deployment tasks.
    """

    application_root: Path
    runtime_data_root: Path
    backup_root: Path
    config_root: Path
    secrets_root: Path

    def __post_init__(self) -> None:
        normalized = {
            "application_root": _absolute_directory(
                self.application_root,
                field_name="application_root",
            ),
            "runtime_data_root": _absolute_directory(
                self.runtime_data_root,
                field_name="runtime_data_root",
            ),
            "backup_root": _absolute_directory(
                self.backup_root,
                field_name="backup_root",
            ),
            "config_root": _absolute_directory(
                self.config_root,
                field_name="config_root",
            ),
            "secrets_root": _absolute_directory(
                self.secrets_root,
                field_name="secrets_root",
            ),
        }

        for field_name, value in normalized.items():
            object.__setattr__(
                self,
                field_name,
                value,
            )

        _require_distinct_roots(
            normalized
        )

    @property
    def knowledge_database(self) -> Path:
        return (
            self.runtime_data_root
            / "knowledge.db"
        )

    @property
    def usage_cost_ledger_database(self) -> Path:
        return (
            self.runtime_data_root
            / "operational"
            / "provider_usage_cost.db"
        )

    @property
    def grounded_generation_database(self) -> Path:
        return (
            self.runtime_data_root
            / "operational"
            / "grounded_generations.db"
        )

    def runtime_environment(self) -> dict[str, str]:
        """
        Return only non-secret filesystem environment values.

        Secret values deliberately remain outside this projection.
        """
        return {
            RUNTIME_DATA_ROOT_ENV: str(
                self.runtime_data_root
            ),
            DATABASE_ENV: str(
                self.knowledge_database
            ),
            USAGE_COST_LEDGER_DATABASE_ENV: str(
                self.usage_cost_ledger_database
            ),
            GROUNDED_GENERATION_DATABASE_ENV: str(
                self.grounded_generation_database
            ),
        }


def _absolute_directory(
    path: Path,
    *,
    field_name: str,
) -> Path:
    if not isinstance(
        path,
        Path,
    ):
        raise TypeError(
            f"{field_name} must be a Path"
        )

    candidate = path.expanduser()
    if not candidate.is_absolute():
        raise ValueError(
            f"{field_name} must be an absolute path"
        )

    return candidate.resolve(
        strict=False
    )


def _require_distinct_roots(
    roots: dict[str, Path],
) -> None:
    items = tuple(
        roots.items()
    )

    for index, (
        left_name,
        left,
    ) in enumerate(items):
        for (
            right_name,
            right,
        ) in items[
            index + 1 :
        ]:
            if (
                _contains(left, right)
                or _contains(right, left)
            ):
                raise ValueError(
                    f"{left_name} and {right_name} "
                    "must be independent deployment roots"
                )


def _contains(
    parent: Path,
    child: Path,
) -> bool:
    try:
        child.relative_to(
            parent
        )
    except ValueError:
        return False
    return True

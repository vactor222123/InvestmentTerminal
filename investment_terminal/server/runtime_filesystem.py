"""Runtime filesystem ownership and confinement for the production server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from investment_terminal.server.runtime_config import (
    GroundedAIServerRuntimeConfig,
)


@dataclass(frozen=True, slots=True)
class GroundedAIServerRuntimeFilesystemContract:
    """
    Validate the optional production data-root contract.

    The contract is intentionally opt-in so existing explicit database paths are
    not silently relocated. When a data root is configured, every operational
    database must resolve inside it before any SQLite store is initialized.
    """

    data_root: Path | None
    knowledge_database: Path
    usage_cost_ledger_database: Path
    grounded_generation_database: Path

    @classmethod
    def from_config(
        cls,
        config: GroundedAIServerRuntimeConfig,
    ) -> "GroundedAIServerRuntimeFilesystemContract":
        if not isinstance(
            config,
            GroundedAIServerRuntimeConfig,
        ):
            raise TypeError(
                "config must be a GroundedAIServerRuntimeConfig"
            )

        return cls(
            data_root=config.runtime_data_root,
            knowledge_database=config.database,
            usage_cost_ledger_database=(
                config.usage_cost_ledger_database
            ),
            grounded_generation_database=(
                config.grounded_generation_database
            ),
        )

    def prepare(self) -> Path | None:
        """
        Prepare and validate the configured runtime data root.

        Legacy mode (no configured root) is deliberately a no-op. This preserves
        the established explicit-path behavior while allowing production
        deployments to opt into strict ownership/confinement.
        """
        if self.data_root is None:
            return None

        root = self._resolve_root(
            self.data_root
        )

        self._require_confined(
            database=self.knowledge_database,
            root=root,
            field_name="knowledge_database",
        )
        ledger = self._require_confined(
            database=self.usage_cost_ledger_database,
            root=root,
            field_name="provider_usage_cost_database",
        )
        generations = self._require_confined(
            database=self.grounded_generation_database,
            root=root,
            field_name="grounded_generation_database",
        )

        self._require_readable_root(
            root
        )
        self._prepare_writable_parent(
            ledger.parent,
            root=root,
            field_name="provider_usage_cost_database",
        )
        self._prepare_writable_parent(
            generations.parent,
            root=root,
            field_name="grounded_generation_database",
        )

        knowledge = self._resolved_path(
            self.knowledge_database
        )
        if knowledge.exists():
            if not knowledge.is_file():
                raise ValueError(
                    "knowledge_database must resolve to a file"
                )
            if not os.access(
                knowledge,
                os.R_OK,
            ):
                raise ValueError(
                    "knowledge_database must be readable"
                )

        return root

    @staticmethod
    def _resolve_root(
        configured_root: Path,
    ) -> Path:
        root = configured_root.expanduser()

        if root.exists() and not root.is_dir():
            raise ValueError(
                "runtime data root must be a directory"
            )

        root.mkdir(
            parents=True,
            exist_ok=True,
        )
        return root.resolve()

    @staticmethod
    def _resolved_path(
        path: Path,
    ) -> Path:
        candidate = path.expanduser()
        if not candidate.is_absolute():
            candidate = (
                Path.cwd()
                / candidate
            )
        return candidate.resolve(
            strict=False
        )

    @classmethod
    def _require_confined(
        cls,
        *,
        database: Path,
        root: Path,
        field_name: str,
    ) -> Path:
        candidate = cls._resolved_path(
            database
        )

        try:
            candidate.relative_to(
                root
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must resolve inside runtime data root"
            ) from exc

        return candidate

    @staticmethod
    def _require_readable_root(
        root: Path,
    ) -> None:
        if not os.access(
            root,
            os.R_OK,
        ):
            raise ValueError(
                "runtime data root must be readable"
            )

    @classmethod
    def _prepare_writable_parent(
        cls,
        parent: Path,
        *,
        root: Path,
        field_name: str,
    ) -> None:
        resolved_parent = parent.resolve(
            strict=False
        )

        try:
            resolved_parent.relative_to(
                root
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} parent must resolve inside runtime data root"
            ) from exc

        resolved_parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Re-resolve after creation so an existing symlink/junction-like parent
        # cannot redirect writes outside the configured root.
        resolved_parent = resolved_parent.resolve()
        try:
            resolved_parent.relative_to(
                root
            )
        except ValueError as exc:
            raise ValueError(
                f"{field_name} parent escapes runtime data root"
            ) from exc

        if not resolved_parent.is_dir():
            raise ValueError(
                f"{field_name} parent must be a directory"
            )
        if not os.access(
            resolved_parent,
            os.W_OK,
        ):
            raise ValueError(
                f"{field_name} parent must be writable"
            )

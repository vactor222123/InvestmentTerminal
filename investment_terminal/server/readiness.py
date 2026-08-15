"""
Local server readiness checks.

Readiness is intentionally network-free. It verifies only runtime prerequisites
that can be checked locally without invoking OpenAI or grounded generation.
"""

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)
from investment_terminal.server.runtime_config import (
    GroundedAIServerRuntimeConfig,
)


@dataclass(frozen=True, slots=True)
class GroundedAIServerReadiness:
    status: str
    checks: dict[str, str]

    @property
    def ready(self) -> bool:
        return self.status == "READY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": dict(self.checks),
        }


class GroundedAIServerReadinessService:
    """Evaluate local production prerequisites without network I/O."""

    def __init__(
        self,
        *,
        config: GroundedAIServerRuntimeConfig,
        environment: Mapping[str, str],
    ) -> None:
        if not isinstance(
            config,
            GroundedAIServerRuntimeConfig,
        ):
            raise TypeError(
                "config must be a GroundedAIServerRuntimeConfig"
            )
        if not isinstance(
            environment,
            Mapping,
        ):
            raise TypeError(
                "environment must be a mapping"
            )

        self._config = config
        self._environment = environment

    def check(self) -> GroundedAIServerReadiness:
        database_status = (
            "READY"
            if self._config.database.is_file()
            else "NOT_READY"
        )
        ledger_status = self._usage_cost_ledger_status()

        secret = self._environment.get(
            self._config.api_key_environment_variable,
            "",
        )
        credential_status = (
            "READY"
            if isinstance(secret, str)
            and bool(secret.strip())
            else "NOT_READY"
        )

        checks = {
            "knowledge_database": database_status,
            "provider_usage_cost_database": ledger_status,
            "provider_credentials": credential_status,
        }
        status = (
            "READY"
            if all(
                value == "READY"
                for value in checks.values()
            )
            else "NOT_READY"
        )

        return GroundedAIServerReadiness(
            status=status,
            checks=checks,
        )

    def _usage_cost_ledger_status(self) -> str:
        database = self._config.usage_cost_ledger_database
        if not database.is_file():
            return "NOT_READY"

        try:
            store = GroundedProviderUsageCostLedgerSQLiteStore(
                database
            )
            schema_version = store.schema_version()
        except (
            OSError,
            sqlite3.DatabaseError,
            TypeError,
            ValueError,
        ):
            return "NOT_READY"

        return (
            "READY"
            if schema_version == store.SCHEMA_VERSION
            else "NOT_READY"
        )

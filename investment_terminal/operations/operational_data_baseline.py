"""Read-only operational data baseline and coverage reporting."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class OperationalState(str, Enum):
    """Explicit operational state without inferred success."""

    CONFIGURED = "CONFIGURED"
    UNCONFIGURED = "UNCONFIGURED"
    READY = "READY"
    ABSENT = "ABSENT"
    ERROR = "ERROR"
    UNMEASURED = "UNMEASURED"


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    provider_identity: str
    roles: tuple[str, ...]
    state: OperationalState
    configuration_source: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_identity",
            normalize_required_text(
                self.provider_identity,
                field_name="provider_identity",
                uppercase=True,
            ),
        )
        normalized_roles = tuple(
            sorted(
                normalize_required_text(
                    role,
                    field_name="role",
                    uppercase=True,
                )
                for role in self.roles
            )
        )
        if not normalized_roles:
            raise ValueError("roles must not be empty")
        if len(normalized_roles) != len(set(normalized_roles)):
            raise ValueError("roles must be unique")
        object.__setattr__(self, "roles", normalized_roles)
        if self.state not in {
            OperationalState.CONFIGURED,
            OperationalState.UNCONFIGURED,
        }:
            raise ValueError("provider state must describe configuration")
        object.__setattr__(
            self,
            "configuration_source",
            normalize_required_text(
                self.configuration_source,
                field_name="configuration_source",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_identity": self.provider_identity,
            "roles": list(self.roles),
            "state": self.state.value,
            "configuration_source": self.configuration_source,
        }


@dataclass(frozen=True, slots=True)
class CoverageRecord:
    identity: str
    count: int
    earliest_at: str | None = None
    latest_at: str | None = None
    attributes: tuple[tuple[str, str | int], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identity",
            normalize_required_text(self.identity, field_name="identity"),
        )
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise TypeError("count must be an integer")
        if self.count < 0:
            raise ValueError("count must not be negative")
        if tuple(sorted(self.attributes)) != self.attributes:
            raise ValueError("attributes must be deterministically ordered")

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "count": self.count,
            "earliest_at": self.earliest_at,
            "latest_at": self.latest_at,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class OperationalStoreCoverage:
    store_identity: str
    configured_path: str | None
    state: OperationalState
    schema_version: int | None
    record_count: int | None
    records: tuple[CoverageRecord, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "store_identity",
            normalize_required_text(
                self.store_identity,
                field_name="store_identity",
                uppercase=True,
            ),
        )
        if self.state not in {
            OperationalState.READY,
            OperationalState.ABSENT,
            OperationalState.ERROR,
        }:
            raise ValueError("store state must be READY, ABSENT, or ERROR")
        if self.state is OperationalState.ERROR and not self.error:
            raise ValueError("ERROR store state requires error")
        if self.state is not OperationalState.ERROR and self.error is not None:
            raise ValueError("only ERROR store state may carry error")
        if tuple(sorted(self.records, key=lambda item: item.identity)) != self.records:
            raise ValueError("records must be deterministically ordered")

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_identity": self.store_identity,
            "configured_path": self.configured_path,
            "state": self.state.value,
            "schema_version": self.schema_version,
            "record_count": self.record_count,
            "records": [item.to_dict() for item in self.records],
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class OperationalDataBaselineInputs:
    market_database: Path | None = None
    maintained_universe_database: Path | None = None
    current_portfolio: Path | None = None
    transaction_database: Path | None = None
    valuation_database: Path | None = None
    external_context_database: Path | None = None
    backup_root: Path | None = None
    workflow_report: Path | None = None


@dataclass(frozen=True, slots=True)
class OperationalDataBaseline:
    generated_at: datetime
    providers: tuple[ProviderCapability, ...]
    stores: tuple[OperationalStoreCoverage, ...]
    refresh_observability: OperationalState = OperationalState.UNMEASURED
    measured_performance: OperationalState = OperationalState.UNMEASURED
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_aware_datetime(self.generated_at, field_name="generated_at")
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if tuple(
            sorted(self.providers, key=lambda item: item.provider_identity)
        ) != self.providers:
            raise ValueError("providers must be deterministically ordered")
        if tuple(
            sorted(self.stores, key=lambda item: item.store_identity)
        ) != self.stores:
            raise ValueError("stores must be deterministically ordered")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "providers": [item.to_dict() for item in self.providers],
            "stores": [item.to_dict() for item in self.stores],
            "refresh_observability": self.refresh_observability.value,
            "measured_performance": self.measured_performance.value,
            "authority": {
                "populated_coverage_is_measured_only": True,
                "analytical_evidence_is_interpretation": False,
                "grants_trade_execution_authority": False,
            },
        }


class OperationalDataBaselineService:
    """Build one deterministic report without mutating inspected sources."""

    def __init__(
        self,
        *,
        inputs: OperationalDataBaselineInputs,
        environment: Mapping[str, str],
        clock,
    ) -> None:
        if not isinstance(inputs, OperationalDataBaselineInputs):
            raise TypeError("inputs must be OperationalDataBaselineInputs")
        self._inputs = inputs
        self._environment = dict(environment)
        self._clock = clock

    def build(self) -> OperationalDataBaseline:
        generated_at = self._clock()
        validate_aware_datetime(generated_at, field_name="generated_at")
        providers = tuple(
            sorted(
                self._provider_capabilities(),
                key=lambda item: item.provider_identity,
            )
        )
        workflow = self._inspect_workflow_report()
        stores = (
            self._inspect_backup_root(),
            self._inspect_candles(),
            self._inspect_external_context(),
            self._inspect_maintained_universes(),
            self._inspect_current_portfolio(),
            self._inspect_transactions(),
            self._inspect_valuations(),
            workflow,
        )
        return OperationalDataBaseline(
            generated_at=generated_at,
            providers=providers,
            stores=tuple(sorted(stores, key=lambda item: item.store_identity)),
            refresh_observability=(
                OperationalState.READY
                if workflow.state is OperationalState.READY
                else OperationalState.UNMEASURED
            ),
            measured_performance=(
                OperationalState.READY
                if workflow.state is OperationalState.READY
                else OperationalState.UNMEASURED
            ),
        )

    def _provider_capabilities(self) -> tuple[ProviderCapability, ...]:
        openai_variable = self._environment.get(
            "INVESTMENT_TERMINAL_OPENAI_API_KEY_ENV",
            "INVESTMENT_TERMINAL_OPENAI_API_KEY",
        ).strip() or "INVESTMENT_TERMINAL_OPENAI_API_KEY"
        return (
            ProviderCapability(
                provider_identity="YAHOO_FINANCE",
                roles=("FUNDAMENTALS", "HISTORICAL_CANDLES"),
                state=OperationalState.CONFIGURED,
                configuration_source="credentialless adapter",
            ),
            ProviderCapability(
                provider_identity="FINNHUB",
                roles=("HISTORICAL_CANDLES", "LATEST_QUOTES"),
                state=self._environment_state("FINNHUB_API_KEY"),
                configuration_source="environment:FINNHUB_API_KEY",
            ),
            ProviderCapability(
                provider_identity="OPENAI",
                roles=("EXPLICIT_GROUNDED_INTERPRETATION",),
                state=self._environment_state(openai_variable),
                configuration_source=f"environment:{openai_variable}",
            ),
            ProviderCapability(
                provider_identity="EXTERNAL_CONTEXT",
                roles=("EVENT", "GEOPOLITICAL", "MACROECONOMIC", "NEWS"),
                state=OperationalState.UNCONFIGURED,
                configuration_source="no concrete adapter configured",
            ),
        )

    def _environment_state(self, variable: str) -> OperationalState:
        return (
            OperationalState.CONFIGURED
            if self._environment.get(variable, "").strip()
            else OperationalState.UNCONFIGURED
        )

    def _inspect_candles(self) -> OperationalStoreCoverage:
        return self._inspect_sqlite(
            "MARKET_CANDLES",
            self._inputs.market_database,
            lambda connection: self._candle_records(connection),
            required_tables=("candles",),
            schema_version=None,
        )

    @staticmethod
    def _candle_records(connection: sqlite3.Connection) -> tuple[CoverageRecord, ...]:
        rows = connection.execute(
            "SELECT symbol, resolution, currency, COUNT(*) AS item_count, "
            "MIN(timestamp) AS earliest_at, MAX(timestamp) AS latest_at "
            "FROM candles GROUP BY symbol, resolution, currency "
            "ORDER BY symbol, resolution, currency"
        ).fetchall()
        return tuple(
            CoverageRecord(
                identity=f"{row['symbol']}:{row['resolution']}:{row['currency']}",
                count=row["item_count"],
                earliest_at=row["earliest_at"],
                latest_at=row["latest_at"],
                attributes=(("freshness", OperationalState.UNMEASURED.value),),
            )
            for row in rows
        )

    def _inspect_maintained_universes(self) -> OperationalStoreCoverage:
        return self._inspect_sqlite(
            "MAINTAINED_UNIVERSES",
            self._inputs.maintained_universe_database,
            self._universe_records,
            required_tables=(
                "maintained_universe_evidence",
                "maintained_universe_members",
                "maintained_universe_metadata",
            ),
            metadata_table="maintained_universe_metadata",
            schema_version=1,
        )

    @staticmethod
    def _universe_records(connection: sqlite3.Connection) -> tuple[CoverageRecord, ...]:
        rows = connection.execute(
            "SELECT evidence.universe_key, evidence.as_of, evidence.payload_json, "
            "COUNT(members.instrument_key) AS member_count "
            "FROM maintained_universe_evidence AS evidence "
            "LEFT JOIN maintained_universe_members AS members "
            "ON members.universe_key = evidence.universe_key "
            "GROUP BY evidence.universe_key, evidence.as_of, evidence.payload_json "
            "ORDER BY evidence.universe_key"
        ).fetchall()
        records: list[CoverageRecord] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            members = payload.get("universe", {}).get("members", [])
            asset_types = Counter(
                item.get("instrument", {}).get("instrument_type", "UNKNOWN")
                for item in members
            )
            attributes = tuple(
                sorted(
                    (f"asset_type_{key}", value)
                    for key, value in asset_types.items()
                )
            )
            records.append(
                CoverageRecord(
                    identity=row["universe_key"],
                    count=row["member_count"],
                    earliest_at=row["as_of"],
                    latest_at=row["as_of"],
                    attributes=attributes,
                )
            )
        return tuple(records)

    def _inspect_transactions(self) -> OperationalStoreCoverage:
        return self._inspect_simple_time_store(
            "PORTFOLIO_TRANSACTIONS",
            self._inputs.transaction_database,
            table="portfolio_transactions",
            timestamp_column="occurred_at",
            metadata_table="portfolio_transaction_metadata",
        )

    def _inspect_valuations(self) -> OperationalStoreCoverage:
        return self._inspect_simple_time_store(
            "PORTFOLIO_VALUATIONS",
            self._inputs.valuation_database,
            table="portfolio_valuation_snapshots",
            timestamp_column="valued_at",
            metadata_table="portfolio_valuation_metadata",
        )

    def _inspect_external_context(self) -> OperationalStoreCoverage:
        return self._inspect_simple_time_store(
            "EXTERNAL_CONTEXT",
            self._inputs.external_context_database,
            table="external_context_evidence",
            timestamp_column="published_at",
            metadata_table="external_context_metadata",
        )

    def _inspect_simple_time_store(
        self,
        identity: str,
        path: Path | None,
        *,
        table: str,
        timestamp_column: str,
        metadata_table: str,
    ) -> OperationalStoreCoverage:
        def records(connection: sqlite3.Connection) -> tuple[CoverageRecord, ...]:
            row = connection.execute(
                f"SELECT COUNT(*) AS item_count, "
                f"MIN({timestamp_column}) AS earliest_at, "
                f"MAX({timestamp_column}) AS latest_at FROM {table}"
            ).fetchone()
            return (
                CoverageRecord(
                    identity=identity,
                    count=row["item_count"],
                    earliest_at=row["earliest_at"],
                    latest_at=row["latest_at"],
                ),
            )

        return self._inspect_sqlite(
            identity,
            path,
            records,
            required_tables=(table, metadata_table),
            metadata_table=metadata_table,
            schema_version=1,
        )

    def _inspect_current_portfolio(self) -> OperationalStoreCoverage:
        path = self._inputs.current_portfolio
        if path is None or not path.is_file():
            return self._absent("CURRENT_PORTFOLIO", path)
        try:
            portfolio = CurrentPortfolioLoader.load(path)
            record = CoverageRecord(
                identity=portfolio.name,
                count=len(portfolio.holdings),
                attributes=(("base_currency", portfolio.policy.base_currency),),
            )
            return OperationalStoreCoverage(
                store_identity="CURRENT_PORTFOLIO",
                configured_path=str(path),
                state=OperationalState.READY,
                schema_version=None,
                record_count=record.count,
                records=(record,),
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            return self._error("CURRENT_PORTFOLIO", path, exc)

    def _inspect_backup_root(self) -> OperationalStoreCoverage:
        path = self._inputs.backup_root
        if path is None or not path.is_dir():
            return self._absent("RUNTIME_BACKUPS", path)
        try:
            records: list[CoverageRecord] = []
            for metadata_path in sorted(path.glob("*/metadata.json")):
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                backup_id = normalize_required_text(
                    payload["backup_set_id"], field_name="backup_set_id"
                )
                records.append(
                    CoverageRecord(
                        identity=backup_id,
                        count=len(payload.get("databases", [])),
                        earliest_at=payload["created_at"],
                        latest_at=payload["created_at"],
                        attributes=(("restore_validation", "UNMEASURED"),),
                    )
                )
            ordered = tuple(sorted(records, key=lambda item: item.identity))
            return OperationalStoreCoverage(
                store_identity="RUNTIME_BACKUPS",
                configured_path=str(path),
                state=OperationalState.READY,
                schema_version=1,
                record_count=len(ordered),
                records=ordered,
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            return self._error("RUNTIME_BACKUPS", path, exc)

    def _inspect_workflow_report(self) -> OperationalStoreCoverage:
        path = self._inputs.workflow_report
        if path is None or not path.is_file():
            return self._absent("WORKFLOW_REPORT", path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            started_at = datetime.fromisoformat(payload["started_at"])
            completed_at = datetime.fromisoformat(payload["completed_at"])
            validate_aware_datetime(started_at, field_name="started_at")
            validate_aware_datetime(completed_at, field_name="completed_at")
            duration_seconds = int((completed_at - started_at).total_seconds())
            if duration_seconds < 0:
                raise ValueError("completed_at must not be earlier than started_at")
            stages = payload["stages"]
            if not isinstance(stages, list):
                raise TypeError("stages must be a JSON array")
            failed = sum(item.get("status") == "FAILED" for item in stages)
            record = CoverageRecord(
                identity=payload["run_id"],
                count=len(stages),
                earliest_at=payload["started_at"],
                latest_at=payload["completed_at"],
                attributes=tuple(
                    sorted(
                        (
                            ("duration_seconds", duration_seconds),
                            ("failed_stage_count", failed),
                        )
                    )
                ),
            )
            return OperationalStoreCoverage(
                store_identity="WORKFLOW_REPORT",
                configured_path=str(path),
                state=OperationalState.READY,
                schema_version=payload.get("schema_version"),
                record_count=1,
                records=(record,),
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            return self._error("WORKFLOW_REPORT", path, exc)

    def _inspect_sqlite(
        self,
        identity: str,
        path: Path | None,
        record_reader,
        *,
        required_tables: tuple[str, ...],
        metadata_table: str | None = None,
        schema_version: int | None,
    ) -> OperationalStoreCoverage:
        if path is None or not path.is_file():
            return self._absent(identity, path)
        try:
            with closing(self._read_only_connection(path)) as connection:
                tables = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                missing = set(required_tables) - tables
                if missing:
                    raise RuntimeError(
                        "missing required tables: " + ", ".join(sorted(missing))
                    )
                if metadata_table is not None:
                    row = connection.execute(
                        f"SELECT value FROM {metadata_table} "
                        "WHERE key = 'schema_version'"
                    ).fetchone()
                    actual_version = int(row["value"]) if row is not None else None
                    if actual_version != schema_version:
                        raise RuntimeError(
                            f"schema version mismatch: expected {schema_version}, "
                            f"found {actual_version}"
                        )
                records = record_reader(connection)
            return OperationalStoreCoverage(
                store_identity=identity,
                configured_path=str(path),
                state=OperationalState.READY,
                schema_version=schema_version,
                record_count=sum(item.count for item in records),
                records=records,
            )
        except (
            json.JSONDecodeError,
            OSError,
            RuntimeError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            return self._error(identity, path, exc)

    @staticmethod
    def _read_only_connection(path: Path):
        connection = sqlite3.connect(
            f"file:{path.resolve().as_posix()}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _absent(identity: str, path: Path | None) -> OperationalStoreCoverage:
        return OperationalStoreCoverage(
            store_identity=identity,
            configured_path=str(path) if path is not None else None,
            state=OperationalState.ABSENT,
            schema_version=None,
            record_count=None,
        )

    @staticmethod
    def _error(
        identity: str,
        path: Path,
        exc: BaseException,
    ) -> OperationalStoreCoverage:
        return OperationalStoreCoverage(
            store_identity=identity,
            configured_path=str(path),
            state=OperationalState.ERROR,
            schema_version=None,
            record_count=None,
            error=f"{type(exc).__name__}: {exc}",
        )

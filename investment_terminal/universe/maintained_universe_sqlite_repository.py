"""SQLite adapter for maintained asset-universe repository semantics."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from investment_terminal.market.instrument_identity_models import (
    InstrumentIdentity,
)
from investment_terminal.market.market_metadata_quality import (
    MarketMetadataProvenance,
    MarketMetadataQualityAssessment,
)
from investment_terminal.universe.maintained_universe_models import (
    AssetUniverseMember,
    MaintainedAssetUniverse,
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.universe.maintained_universe_repository import (
    MaintainedAssetUniverseRepository,
)
from investment_terminal.universe.maintained_universe_sqlite_store import (
    MaintainedAssetUniverseSQLiteStore,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
)


class SQLiteMaintainedAssetUniverseRepository(
    MaintainedAssetUniverseRepository
):
    """Persist append-only maintained-universe evidence in SQLite."""

    def __init__(self, store: MaintainedAssetUniverseSQLiteStore) -> None:
        if not isinstance(store, MaintainedAssetUniverseSQLiteStore):
            raise TypeError(
                "store must be a MaintainedAssetUniverseSQLiteStore"
            )
        self.store = store

    def add(
        self,
        evidence: MaintainedAssetUniverseEvidence,
    ) -> MaintainedAssetUniverseEvidence:
        if not isinstance(evidence, MaintainedAssetUniverseEvidence):
            raise TypeError(
                "evidence must be MaintainedAssetUniverseEvidence"
            )
        universe = evidence.universe
        provenance = evidence.provenance
        payload = json.dumps(
            evidence.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        try:
            with self.store.transaction() as connection:
                connection.execute(
                    "INSERT INTO maintained_universe_evidence "
                    "(universe_key, universe_id, version, as_of, source, "
                    "source_record_key, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        universe.universe_key,
                        universe.universe_id,
                        universe.version,
                        universe.as_of.isoformat(),
                        provenance.source,
                        provenance.source_record_id or "",
                        payload,
                    ),
                )
                connection.executemany(
                    "INSERT INTO maintained_universe_members "
                    "(universe_key, instrument_key) VALUES (?, ?)",
                    tuple(
                        (
                            universe.universe_key,
                            member.instrument.instrument_key,
                        )
                        for member in universe.members
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Maintained asset universe identity already exists"
            ) from exc
        return evidence

    def get(
        self,
        universe_key: str,
    ) -> MaintainedAssetUniverseEvidence | None:
        normalized = normalize_required_text(
            universe_key,
            field_name="universe_key",
            uppercase=True,
        )
        rows = self._query(
            "SELECT payload_json FROM maintained_universe_evidence "
            "WHERE universe_key = ?",
            (normalized,),
        )
        return self._from_row(rows[0]) if rows else None

    def list_all(self) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        return self._evidence(self._query(
            "SELECT payload_json FROM maintained_universe_evidence "
            + self._order_by(),
        ))

    def list_between(
        self,
        observed_from: datetime,
        observed_until: datetime,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        start = validate_aware_datetime(
            observed_from,
            field_name="observed_from",
        )
        end = validate_aware_datetime(
            observed_until,
            field_name="observed_until",
        )
        if end <= start:
            raise ValueError(
                "observed_until must be later than observed_from"
            )
        return self._evidence(self._query(
            "SELECT payload_json FROM maintained_universe_evidence "
            "WHERE as_of >= ? AND as_of < ? "
            + self._order_by(),
            (start.isoformat(), end.isoformat()),
        ))

    def list_for_universe(
        self,
        universe_id: str,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        normalized = normalize_required_text(
            universe_id,
            field_name="universe_id",
            uppercase=True,
        )
        return self._evidence(self._query(
            "SELECT payload_json FROM maintained_universe_evidence "
            "WHERE universe_id = ? "
            + self._order_by(),
            (normalized,),
        ))

    def list_for_instrument(
        self,
        instrument_key: str,
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        normalized = normalize_required_text(
            instrument_key,
            field_name="instrument_key",
            uppercase=True,
        )
        return self._evidence(self._query(
            "SELECT evidence.payload_json "
            "FROM maintained_universe_evidence evidence "
            "JOIN maintained_universe_members members "
            "ON members.universe_key = evidence.universe_key "
            "WHERE members.instrument_key = ? "
            + self._order_by("evidence"),
            (normalized,),
        ))

    def latest(
        self,
        universe_id: str,
    ) -> MaintainedAssetUniverseEvidence | None:
        normalized = normalize_required_text(
            universe_id,
            field_name="universe_id",
            uppercase=True,
        )
        rows = self._query(
            "SELECT payload_json FROM maintained_universe_evidence "
            "WHERE universe_id = ? "
            "ORDER BY as_of DESC, version DESC, source DESC, "
            "source_record_key DESC, universe_key DESC LIMIT 1",
            (normalized,),
        )
        return self._from_row(rows[0]) if rows else None

    def _query(
        self,
        sql: str,
        parameters: tuple[object, ...] = (),
    ) -> list[sqlite3.Row]:
        self.store.initialize()
        with self.store.connect() as connection:
            return connection.execute(sql, parameters).fetchall()

    @staticmethod
    def _order_by(alias: str | None = None) -> str:
        prefix = f"{alias}." if alias is not None else ""
        return (
            "ORDER BY "
            f"{prefix}as_of, {prefix}universe_id, {prefix}version, "
            f"{prefix}source, {prefix}source_record_key, "
            f"{prefix}universe_key"
        )

    @classmethod
    def _evidence(
        cls,
        rows: list[sqlite3.Row],
    ) -> tuple[MaintainedAssetUniverseEvidence, ...]:
        return tuple(cls._from_row(row) for row in rows)

    @classmethod
    def _from_row(
        cls,
        row: sqlite3.Row,
    ) -> MaintainedAssetUniverseEvidence:
        payload = json.loads(row["payload_json"])
        universe_payload = payload["universe"]
        provenance_payload = payload["provenance"]
        quality_payload = payload["quality"]
        universe = MaintainedAssetUniverse(
            universe_id=universe_payload["universe_id"],
            version=universe_payload["version"],
            name=universe_payload["name"],
            description=universe_payload["description"],
            as_of=datetime.fromisoformat(universe_payload["as_of"]),
            members=tuple(
                AssetUniverseMember(
                    instrument=cls._identity(item["instrument"]),
                    included_at=datetime.fromisoformat(item["included_at"]),
                    inclusion_reason=item["inclusion_reason"],
                )
                for item in universe_payload["members"]
            ),
        )
        provenance = MarketMetadataProvenance(
            source=provenance_payload["source"],
            source_record_id=provenance_payload["source_record_id"],
            observed_at=datetime.fromisoformat(
                provenance_payload["observed_at"]
            ),
            fetched_at=datetime.fromisoformat(
                provenance_payload["fetched_at"]
            ),
            checksum_sha256=provenance_payload["checksum_sha256"],
        )
        quality = MarketMetadataQualityAssessment(
            status=quality_payload["status"],
            checked_at=datetime.fromisoformat(quality_payload["checked_at"]),
            maximum_age_days=quality_payload["maximum_age_days"],
            age_days=quality_payload["age_days"],
            missing_provenance_fields=tuple(
                quality_payload["missing_provenance_fields"]
            ),
            warnings=tuple(quality_payload["warnings"]),
        )
        return MaintainedAssetUniverseEvidence(
            universe=universe,
            provenance=provenance,
            quality=quality,
        )

    @staticmethod
    def _identity(payload: dict[str, Any]) -> InstrumentIdentity:
        return InstrumentIdentity(
            symbol=payload["symbol"],
            name=payload["name"],
            instrument_type=payload["instrument_type"],
            currency=payload["currency"],
            isin=payload["isin"],
            exchange_ticker=payload["exchange_ticker"],
            exchange_code=payload["exchange_code"],
        )

"""
Snapshot compatibility policy for historical comparison workflows.
"""

from dataclasses import dataclass
from typing import Any, Iterable

from investment_terminal.history.historical_comparison_facts import (
    HistoricalComparisonFacts,
)
from investment_terminal.history.historical_import_state_models import (
    HistoricalImportState,
)
from investment_terminal.history.historical_snapshot_models import (
    HistoricalSnapshot,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class SnapshotCompatibilityResult:
    """Immutable compatibility assessment for two historical snapshots."""

    earlier_snapshot_id: str
    later_snapshot_id: str
    status: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    source_status_changed: bool

    SUPPORTED_STATUSES = (
        "COMPATIBLE",
        "PARTIALLY_COMPATIBLE",
        "INCOMPATIBLE",
    )

    def __post_init__(self) -> None:
        earlier = HistoricalSnapshot._normalize_uuid(
            self.earlier_snapshot_id,
            field_name="earlier_snapshot_id",
        )
        later = HistoricalSnapshot._normalize_uuid(
            self.later_snapshot_id,
            field_name="later_snapshot_id",
        )

        if earlier == later:
            raise ValueError(
                "earlier_snapshot_id and later_snapshot_id must differ"
            )

        object.__setattr__(
            self,
            "earlier_snapshot_id",
            earlier,
        )
        object.__setattr__(
            self,
            "later_snapshot_id",
            later,
        )

        status = normalize_required_text(
            self.status,
            field_name="status",
            uppercase=True,
        )
        if status not in self.SUPPORTED_STATUSES:
            raise ValueError(
                "status must be one of: "
                + ", ".join(
                    self.SUPPORTED_STATUSES
                )
            )
        object.__setattr__(
            self,
            "status",
            status,
        )

        for field_name in (
            "blockers",
            "warnings",
        ):
            value = getattr(
                self,
                field_name,
            )
            if not isinstance(
                value,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            normalized = tuple(
                normalize_required_text(
                    item,
                    field_name=field_name[:-1],
                )
                for item in value
            )
            object.__setattr__(
                self,
                field_name,
                normalized,
            )

        if not isinstance(
            self.source_status_changed,
            bool,
        ):
            raise TypeError(
                "source_status_changed must be a boolean"
            )

        if self.status == "INCOMPATIBLE" and not self.blockers:
            raise ValueError(
                "INCOMPATIBLE requires at least one blocker"
            )

        if self.status != "INCOMPATIBLE" and self.blockers:
            raise ValueError(
                "only INCOMPATIBLE may contain blockers"
            )

    @property
    def may_compare(
        self,
    ) -> bool:
        return self.status != "INCOMPATIBLE"

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "earlier_snapshot_id": self.earlier_snapshot_id,
            "later_snapshot_id": self.later_snapshot_id,
            "status": self.status,
            "may_compare": self.may_compare,
            "blockers": list(
                self.blockers
            ),
            "warnings": list(
                self.warnings
            ),
            "source_status_changed": (
                self.source_status_changed
            ),
        }


class HistoricalSnapshotCompatibilityService:
    """
    Determine whether two snapshots may be meaningfully compared.

    This service contains compatibility policy only. Persistence access remains
    in History repositories; callers supply typed snapshots, import states and
    normalized comparison facts.
    """

    def __init__(
        self,
        *,
        supported_package_schemas: Iterable[str],
    ) -> None:
        schemas = tuple(
            normalize_required_text(
                schema,
                field_name="supported package schema",
            )
            for schema in supported_package_schemas
        )

        if not schemas:
            raise ValueError(
                "supported_package_schemas must not be empty"
            )

        if len(
            set(
                schemas
            )
        ) != len(
            schemas
        ):
            raise ValueError(
                "supported_package_schemas must not contain duplicates"
            )

        self.supported_package_schemas = schemas

    def assess(
        self,
        *,
        earlier_snapshot: HistoricalSnapshot,
        later_snapshot: HistoricalSnapshot,
        earlier_state: HistoricalImportState,
        later_state: HistoricalImportState,
        earlier_facts: HistoricalComparisonFacts,
        later_facts: HistoricalComparisonFacts,
    ) -> SnapshotCompatibilityResult:
        """Assess compatibility without computing any comparison deltas."""
        self._validate_inputs(
            earlier_snapshot=earlier_snapshot,
            later_snapshot=later_snapshot,
            earlier_state=earlier_state,
            later_state=later_state,
            earlier_facts=earlier_facts,
            later_facts=later_facts,
        )

        blockers: list[str] = []
        warnings: list[str] = []

        if (
            earlier_snapshot.generated_at
            >= later_snapshot.generated_at
        ):
            blockers.append(
                "Earlier snapshot generated_at must precede later snapshot"
            )

        if (
            earlier_snapshot.package_schema_version
            not in self.supported_package_schemas
        ):
            blockers.append(
                "Earlier snapshot package schema is not supported"
            )

        if (
            later_snapshot.package_schema_version
            not in self.supported_package_schemas
        ):
            blockers.append(
                "Later snapshot package schema is not supported"
            )

        if (
            earlier_snapshot.package_schema_version
            != later_snapshot.package_schema_version
        ):
            warnings.append(
                "Snapshot package schema versions differ"
            )

        if (
            earlier_state.status != "IMPORTED"
            or later_state.status != "IMPORTED"
        ):
            warnings.append(
                "One or both snapshots do not have IMPORTED state"
            )

        if (
            earlier_facts.portfolio_name is not None
            and later_facts.portfolio_name is not None
            and earlier_facts.portfolio_name
            != later_facts.portfolio_name
        ):
            blockers.append(
                "Portfolio identity does not match"
            )

        if (
            earlier_facts.base_currency is not None
            and later_facts.base_currency is not None
            and earlier_facts.base_currency
            != later_facts.base_currency
        ):
            blockers.append(
                "Base currency does not match"
            )

        source_status_changed = (
            earlier_facts.source_status
            != later_facts.source_status
        )

        if source_status_changed:
            warnings.append(
                "Portfolio source status differs between snapshots"
            )

        if not earlier_facts.portfolio_summary_present:
            warnings.append(
                "Earlier snapshot portfolio summary is missing"
            )

        if not later_facts.portfolio_summary_present:
            warnings.append(
                "Later snapshot portfolio summary is missing"
            )

        if not earlier_facts.has_any_detail_rows:
            warnings.append(
                "Earlier snapshot has no structured detail rows"
            )

        if not later_facts.has_any_detail_rows:
            warnings.append(
                "Later snapshot has no structured detail rows"
            )

        if blockers:
            status = "INCOMPATIBLE"
        elif warnings:
            status = "PARTIALLY_COMPATIBLE"
        else:
            status = "COMPATIBLE"

        return SnapshotCompatibilityResult(
            earlier_snapshot_id=earlier_snapshot.snapshot_id,
            later_snapshot_id=later_snapshot.snapshot_id,
            status=status,
            blockers=tuple(
                blockers
            ),
            warnings=tuple(
                warnings
            ),
            source_status_changed=source_status_changed,
        )

    @staticmethod
    def _validate_inputs(
        *,
        earlier_snapshot: HistoricalSnapshot,
        later_snapshot: HistoricalSnapshot,
        earlier_state: HistoricalImportState,
        later_state: HistoricalImportState,
        earlier_facts: HistoricalComparisonFacts,
        later_facts: HistoricalComparisonFacts,
    ) -> None:
        for field_name, value, expected_type in (
            (
                "earlier_snapshot",
                earlier_snapshot,
                HistoricalSnapshot,
            ),
            (
                "later_snapshot",
                later_snapshot,
                HistoricalSnapshot,
            ),
            (
                "earlier_state",
                earlier_state,
                HistoricalImportState,
            ),
            (
                "later_state",
                later_state,
                HistoricalImportState,
            ),
            (
                "earlier_facts",
                earlier_facts,
                HistoricalComparisonFacts,
            ),
            (
                "later_facts",
                later_facts,
                HistoricalComparisonFacts,
            ),
        ):
            if not isinstance(
                value,
                expected_type,
            ):
                raise TypeError(
                    f"{field_name} must be a {expected_type.__name__}"
                )

        if (
            earlier_snapshot.snapshot_id
            == later_snapshot.snapshot_id
        ):
            raise ValueError(
                "earlier_snapshot and later_snapshot must differ"
            )

        if (
            earlier_state.snapshot_id
            != earlier_snapshot.snapshot_id
        ):
            raise ValueError(
                "earlier_state does not belong to earlier_snapshot"
            )

        if (
            later_state.snapshot_id
            != later_snapshot.snapshot_id
        ):
            raise ValueError(
                "later_state does not belong to later_snapshot"
            )

        if (
            earlier_facts.snapshot_id
            != earlier_snapshot.snapshot_id
        ):
            raise ValueError(
                "earlier_facts does not belong to earlier_snapshot"
            )

        if (
            later_facts.snapshot_id
            != later_snapshot.snapshot_id
        ):
            raise ValueError(
                "later_facts does not belong to later_snapshot"
            )

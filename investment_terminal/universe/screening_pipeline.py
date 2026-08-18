"""Deterministic, policy-driven screening for maintained asset universes."""

from dataclasses import dataclass
from datetime import datetime
from operator import eq, ge, gt, le, lt
from typing import Any, Callable

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.universe.maintained_universe_models import (
    MaintainedAssetUniverseEvidence,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)

SCREENING_OPERATORS = ("LT", "LTE", "EQ", "GTE", "GT")
SCREENING_MISSING_DATA_ACTIONS = ("FAIL", "REVIEW")


@dataclass(frozen=True, slots=True)
class ScreeningCriterion:
    criterion_id: str
    metric: str
    operator: str
    threshold: float
    unit: str
    missing_data_action: str

    def __post_init__(self) -> None:
        for name in ("criterion_id", "metric"):
            object.__setattr__(self, name, normalize_required_text(
                getattr(self, name), field_name=name,
            ))
        for name, choices in (
            ("operator", SCREENING_OPERATORS),
            ("missing_data_action", SCREENING_MISSING_DATA_ACTIONS),
        ):
            value = normalize_required_text(
                getattr(self, name), field_name=name, uppercase=True,
            )
            if value not in choices:
                raise ValueError(f"{name} must be one of: " + ", ".join(choices))
            object.__setattr__(self, name, value)
        object.__setattr__(self, "threshold", validate_finite_number(
            self.threshold, field_name="threshold",
        ))
        object.__setattr__(self, "unit", normalize_required_text(
            self.unit, field_name="unit", uppercase=True,
        ))

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScreeningPolicy:
    policy_id: str
    version: int
    effective_at: datetime
    criteria: tuple[ScreeningCriterion, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", normalize_required_text(
            self.policy_id, field_name="policy_id",
        ))
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        validate_aware_datetime(self.effective_at, field_name="effective_at")
        if not isinstance(self.criteria, tuple) or not self.criteria:
            raise ValueError("criteria must be a non-empty tuple")
        if any(not isinstance(item, ScreeningCriterion) for item in self.criteria):
            raise TypeError("criteria must contain ScreeningCriterion values")
        ids = tuple(item.criterion_id for item in self.criteria)
        metrics = tuple(item.metric for item in self.criteria)
        if ids != tuple(sorted(ids)):
            raise ValueError("criteria must be ordered by criterion_id")
        if len(ids) != len(set(ids)) or len(metrics) != len(set(metrics)):
            raise ValueError("criteria must have unique ids and metrics")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "effective_at": self.effective_at.isoformat(),
            "criteria": [item.to_dict() for item in self.criteria],
        }


@dataclass(frozen=True, slots=True)
class ScreeningMetricEvidence:
    instrument: InstrumentIdentity
    metric: str
    value: float
    unit: str
    observed_at: datetime
    evidence_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        for name, uppercase in (("metric", False), ("unit", True), ("evidence_id", False)):
            object.__setattr__(self, name, normalize_required_text(
                getattr(self, name), field_name=name, uppercase=uppercase,
            ))
        object.__setattr__(self, "value", validate_finite_number(
            self.value, field_name="value",
        ))
        validate_aware_datetime(self.observed_at, field_name="observed_at")


@dataclass(frozen=True, slots=True)
class ScreeningCriterionEvaluation:
    criterion_id: str
    metric: str
    operator: str
    threshold: float
    unit: str
    observed_value: float | None
    evidence_id: str | None
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class ScreeningCandidateEvidence:
    instrument: InstrumentIdentity
    status: str
    criteria: tuple[ScreeningCriterionEvaluation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentIdentity):
            raise TypeError("instrument must be an InstrumentIdentity")
        if self.status not in ("PASS", "FAIL", "REVIEW"):
            raise ValueError("status must be PASS, FAIL, or REVIEW")
        if not isinstance(self.criteria, tuple) or not self.criteria:
            raise ValueError("criteria must be a non-empty tuple")
        if any(not isinstance(item, ScreeningCriterionEvaluation) for item in self.criteria):
            raise TypeError("criteria must contain ScreeningCriterionEvaluation values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "status": self.status,
            "criteria": [item.to_dict() for item in self.criteria],
        }


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    universe: MaintainedAssetUniverseEvidence
    policy: ScreeningPolicy
    evaluated_at: datetime
    candidates: tuple[ScreeningCandidateEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.universe, MaintainedAssetUniverseEvidence):
            raise TypeError("universe must be MaintainedAssetUniverseEvidence")
        if not isinstance(self.policy, ScreeningPolicy):
            raise TypeError("policy must be a ScreeningPolicy")
        validate_aware_datetime(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a tuple")
        if any(not isinstance(item, ScreeningCandidateEvidence) for item in self.candidates):
            raise TypeError("candidates must contain ScreeningCandidateEvidence values")
        keys = tuple(item.instrument.instrument_key for item in self.candidates)
        expected = tuple(item.instrument.instrument_key for item in self.universe.universe.members)
        if keys != expected:
            raise ValueError("candidates must match universe members in canonical order")

    @property
    def status_counts(self) -> dict[str, int]:
        return {
            status: sum(item.status == status for item in self.candidates)
            for status in ("PASS", "FAIL", "REVIEW")
        }

    @property
    def passing_instrument_keys(self) -> tuple[str, ...]:
        return tuple(
            item.instrument.instrument_key
            for item in self.candidates if item.status == "PASS"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "universe": self.universe.to_dict(),
            "policy": self.policy.to_dict(),
            "evaluated_at": self.evaluated_at.isoformat(),
            "status_counts": self.status_counts,
            "passing_instrument_keys": list(self.passing_instrument_keys),
            "ranking_authorized": False,
            "recommendation_authorized": False,
            "candidates": [item.to_dict() for item in self.candidates],
        }


class ScreeningPipeline:
    """Apply caller-owned thresholds without ranking or recommendation."""

    _OPERATORS: dict[str, Callable[[float, float], bool]] = {
        "LT": lt, "LTE": le, "EQ": eq, "GTE": ge, "GT": gt,
    }

    @classmethod
    def evaluate(
        cls,
        universe: MaintainedAssetUniverseEvidence,
        policy: ScreeningPolicy,
        metrics: tuple[ScreeningMetricEvidence, ...],
        *,
        evaluated_at: datetime,
    ) -> ScreeningResult:
        if not isinstance(universe, MaintainedAssetUniverseEvidence):
            raise TypeError("universe must be MaintainedAssetUniverseEvidence")
        if not isinstance(policy, ScreeningPolicy):
            raise TypeError("policy must be a ScreeningPolicy")
        validate_aware_datetime(evaluated_at, field_name="evaluated_at")
        if evaluated_at < max(universe.quality.checked_at, policy.effective_at):
            raise ValueError("evaluated_at must not precede universe quality or policy")
        if not isinstance(metrics, tuple) or any(
            not isinstance(item, ScreeningMetricEvidence) for item in metrics
        ):
            raise TypeError("metrics must be a tuple of ScreeningMetricEvidence values")

        member_keys = {item.instrument.instrument_key for item in universe.universe.members}
        policy_metrics = {item.metric for item in policy.criteria}
        indexed: dict[tuple[str, str], ScreeningMetricEvidence] = {}
        for item in metrics:
            key = (item.instrument.instrument_key, item.metric)
            if key[0] not in member_keys:
                raise ValueError("metric contains an instrument outside universe")
            if item.metric not in policy_metrics:
                raise ValueError("metric is not referenced by screening policy")
            if item.observed_at > evaluated_at:
                raise ValueError("metric observed_at must not be after evaluated_at")
            if key in indexed:
                raise ValueError("metrics must be unique by instrument and metric")
            indexed[key] = item

        candidates = []
        for member in universe.universe.members:
            evaluations = tuple(
                cls._criterion(
                    criterion,
                    indexed.get((member.instrument.instrument_key, criterion.metric)),
                )
                for criterion in policy.criteria
            )
            statuses = {item.status for item in evaluations}
            status = "FAIL" if "FAIL" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"
            candidates.append(ScreeningCandidateEvidence(member.instrument, status, evaluations))
        return ScreeningResult(universe, policy, evaluated_at, tuple(candidates))

    @classmethod
    def _criterion(
        cls,
        criterion: ScreeningCriterion,
        metric: ScreeningMetricEvidence | None,
    ) -> ScreeningCriterionEvaluation:
        values = (
            criterion.criterion_id, criterion.metric, criterion.operator,
            criterion.threshold, criterion.unit,
        )
        if metric is None:
            return ScreeningCriterionEvaluation(
                *values, None, None, criterion.missing_data_action, "METRIC_MISSING",
            )
        if metric.unit != criterion.unit:
            return ScreeningCriterionEvaluation(
                *values, metric.value, metric.evidence_id, "FAIL", "UNIT_MISMATCH",
            )
        passed = cls._OPERATORS[criterion.operator](metric.value, criterion.threshold)
        return ScreeningCriterionEvaluation(
            *values, metric.value, metric.evidence_id,
            "PASS" if passed else "FAIL",
            "CONDITION_MET" if passed else "CONDITION_NOT_MET",
        )

"""Versioned corporate-action context, without changing candle price basis."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import re

from investment_terminal.market.corporate_actions import (
    ACTION_KINDS, CorporateActionSnapshot, LIMITATIONS, canonical_bytes,
)
from investment_terminal.utils.validation import validate_aware_datetime


@dataclass(frozen=True, slots=True)
class ResearchActionPolicy:
    as_of: datetime
    maximum_age_days: int

    def __post_init__(self):
        validate_aware_datetime(self.as_of, field_name="actions as_of")
        if self.as_of.utcoffset() != timedelta(0):
            raise ValueError("Action evaluation time must be UTC")
        if (type(self.maximum_age_days) is not int
                or not 1 <= self.maximum_age_days <= 365):
            raise ValueError("Action maximum age must be 1 through 365 days")


def project_action_context(*, symbol, currency, start, end, policy,
                           snapshot=None, source_sha256=None):
    """Availability describes supplied evidence, never source completeness."""
    if not isinstance(policy, ResearchActionPolicy):
        raise TypeError("policy must be ResearchActionPolicy")
    for moment in (start, end):
        validate_aware_datetime(moment, field_name="research window")
        if moment.utcoffset() != timedelta(0) or moment.time() != datetime.min.time():
            raise ValueError("Research action window must use UTC midnight")
    if not start < end <= policy.as_of or end - start > timedelta(days=3660):
        raise ValueError("Research action window is invalid")
    summary = {
        "schema_version": 1,
        "observed_layer": "YFINANCE_HISTORY_FRAME",
        "use": "FACTUAL_CONTEXT_ONLY",
        "as_of_utc": policy.as_of.isoformat(),
        "maximum_age_days": policy.maximum_age_days,
        "availability": "MISSING",
        "source_snapshot_sha256": None,
        "snapshot_document_sha256": None,
        "source_content_sha256": None,
        "event_counts": None,
        "capital_gains_field_present": None,
        "action_completeness": "UNKNOWN",
        "limitations": list(LIMITATIONS),
    }
    if snapshot is None:
        if source_sha256 is not None:
            raise ValueError("Missing snapshot cannot have a source checksum")
        return {**deepcopy(summary), "snapshot": None}, summary
    if not isinstance(snapshot, CorporateActionSnapshot):
        raise TypeError("snapshot must be CorporateActionSnapshot")
    if (not isinstance(source_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None):
        raise ValueError("Action snapshot checksum is invalid")
    if (snapshot.symbol != symbol or snapshot.quote_currency != currency
            or snapshot.start != start or snapshot.end != end):
        raise ValueError("Action snapshot identity, currency or window mismatch")
    if snapshot.fetched_at > policy.as_of:
        raise ValueError("Action snapshot is from after evaluation time")
    document = snapshot.to_dict()
    summary.update({
        "availability": ("STALE" if policy.as_of - snapshot.fetched_at
                         > timedelta(days=policy.maximum_age_days) else "AVAILABLE"),
        "source_snapshot_sha256": source_sha256,
        "snapshot_document_sha256": sha256(canonical_bytes(document)).hexdigest(),
        "source_content_sha256": document["content_sha256"],
        "event_counts": {
            kind: sum(event.kind == kind for event in snapshot.events)
            for kind in ACTION_KINDS
        },
        "capital_gains_field_present": snapshot.capital_gains_present,
    })
    return {**deepcopy(summary), "snapshot": document}, summary


def attach_action_context(private, report, *, policy, snapshot=None,
                          source_sha256=None):
    """Create detached schema-2 artifacts from the unchanged schema-1 pair."""
    if (type(private.get("schema_version")) is not int
            or private["schema_version"] != 1
            or type(report.get("schema_version")) is not int
            or report["schema_version"] != 1
            or "corporate_actions" in private or "corporate_actions" in report):
        raise ValueError("Action attachment requires a schema-1 pair")
    private_context, summary = project_action_context(
        symbol=private["symbol"], currency=private["currency"],
        start=datetime.fromisoformat(private["history_start"]),
        end=datetime.fromisoformat(private["end"]), policy=policy,
        snapshot=snapshot, source_sha256=source_sha256,
    )
    return (
        {**deepcopy(private), "schema_version": 2, "corporate_actions": private_context},
        {**deepcopy(report), "schema_version": 2, "corporate_actions": summary},
    )


def verified_schema1_pair(private, report):
    """Recompute every schema-2 context field before legacy pair verification."""
    try:
        if (type(private["schema_version"]) is not int or private["schema_version"] != 2
                or type(report["schema_version"]) is not int or report["schema_version"] != 2):
            raise ValueError("Expected matching schema 2")
        context = private["corporate_actions"]
        summary = report["corporate_actions"]
        policy = ResearchActionPolicy(
            datetime.fromisoformat(summary["as_of_utc"]), summary["maximum_age_days"],
        )
        raw_snapshot = context["snapshot"]
        snapshot = (CorporateActionSnapshot.from_dict(raw_snapshot)
                    if raw_snapshot is not None else None)
        expected_private, expected_report = project_action_context(
            symbol=private["symbol"], currency=private["currency"],
            start=datetime.fromisoformat(private["history_start"]),
            end=datetime.fromisoformat(private["end"]), policy=policy,
            snapshot=snapshot, source_sha256=summary["source_snapshot_sha256"],
        )
        if (canonical_bytes(context) != canonical_bytes(expected_private)
                or canonical_bytes(summary) != canonical_bytes(expected_report)):
            raise ValueError("Research action context mismatch")
        base_private = {key: value for key, value in private.items() if key != "corporate_actions"}
        base_report = {key: value for key, value in report.items() if key != "corporate_actions"}
        return ({**base_private, "schema_version": 1},
                {**base_report, "schema_version": 1})
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid research corporate-action context") from exc

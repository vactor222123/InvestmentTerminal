"""Schema-2 redacted provenance boundary for a yfinance history frame."""

from __future__ import annotations

import re
from typing import Any


_VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")


def validate_yfinance_version(value: object) -> str:
    if not isinstance(value, str) or not _VERSION_PATTERN.fullmatch(value):
        raise ValueError("yfinance_version must be a three-part release version")
    return value


def to_schema2_report(
    schema1_result: dict[str, Any], *, yfinance_version: str
) -> dict[str, Any]:
    """Relabel a qualified normalized frame without inventing raw evidence."""
    if schema1_result.get("schema_version") != 1:
        raise ValueError("schema-2 conversion requires a schema-1 result")
    version = validate_yfinance_version(yfinance_version)

    return {
        "schema_version": 2,
        "provider_identity": schema1_result["provider_identity"],
        "observed_layer": "YFINANCE_HISTORY_FRAME",
        "qualification_scope": "NORMALIZED_FRAME_SHAPE_ONLY",
        "adapter": {"name": "YFINANCE", "version": version},
        "request": schema1_result["request"],
        "status": schema1_result["status"],
        "row_count": schema1_result["row_count"],
        "normalized_frame_fields": schema1_result["fields"],
        "failure_category": schema1_result["failure_category"],
        "raw_source_evidence": {
            "adjclose_indicator_presence": "UNKNOWN",
            "dividend_events_presence": "UNKNOWN",
            "split_events_presence": "UNKNOWN",
            "capital_gains_events_presence": "UNKNOWN",
            "action_completeness": "UNKNOWN",
        },
        "limitations": [
            *schema1_result["limitations"],
            "normalized columns may be synthesized by yfinance",
            "raw Yahoo field presence and action completeness were not inspected",
        ],
    }

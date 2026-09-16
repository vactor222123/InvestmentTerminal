from datetime import datetime, timedelta, timezone

import pytest

from investment_terminal.operations.manifest_partial_causal_evidence import (
    ManifestPartialCausalEvidenceDiagnostic,
)
from tests.test_manifest_partial_failure_qualification import evidence


NOW = datetime(2026, 9, 16, 18, 0, tzinfo=timezone.utc)


def schema4_evidence(*, causal=True):
    _, _, selection, checkpoint, selected = evidence()
    checkpoint["schema_version"] = 4
    outcome = checkpoint["outcomes"][selected.symbol]
    outcome["causal_failure_evidence"] = (
        {
            "category": "NO_PRICE_DATA",
            "exception_type_chain": [
                "investment_terminal.utils.exceptions.APIError",
                "yfinance.exceptions.YFPricesMissingError",
            ],
        }
        if causal
        else None
    )
    return selection, checkpoint, selected


def diagnostic(*times):
    values = iter(times or (NOW, NOW + timedelta(seconds=1)))
    return ManifestPartialCausalEvidenceDiagnostic(clock=lambda: next(values))


def test_projects_stored_causal_evidence_without_identity_or_mutation():
    selection, checkpoint, selected = schema4_evidence()
    original = {
        key: dict(value) for key, value in checkpoint["outcomes"].items()
    }

    report = diagnostic().run(selection, checkpoint)

    assert report["status"] == "EVIDENCE_AVAILABLE"
    assert report["selection"] == {
        "requested_count": 3,
        "checkpoint_outcome_count": 2,
        "missing_count": 1,
        "failed_candidate_count": 1,
        "selected_count": 1,
        "checkpoint_failure_types": ["APIError"],
    }
    assert report["causal_failure_evidence"] == {
        "category": "NO_PRICE_DATA",
        "exception_type_chain": [
            "investment_terminal.utils.exceptions.APIError",
            "yfinance.exceptions.YFPricesMissingError",
        ],
    }
    assert selected.symbol not in str(report)
    assert checkpoint["outcomes"] == original


def test_reports_legacy_null_evidence_without_inference():
    selection, checkpoint, _ = schema4_evidence(causal=False)

    report = diagnostic().run(selection, checkpoint)

    assert report["status"] == "LEGACY_EVIDENCE_UNAVAILABLE"
    assert report["causal_failure_evidence"] is None
    assert report["failure"] is None


def test_rejects_malformed_causal_evidence():
    selection, checkpoint, _ = schema4_evidence()
    failed = next(
        value
        for value in checkpoint["outcomes"].values()
        if value["status"] == "FAILED"
    )
    failed["causal_failure_evidence"]["exception_type_chain"] = ["private"]

    with pytest.raises(ValueError, match="causal type chain"):
        diagnostic().run(selection, checkpoint)


def test_rejects_nonpartial_checkpoint():
    selection, checkpoint, _ = schema4_evidence()
    missing = selection.request.items[2]
    checkpoint["outcomes"][missing.symbol] = {
        "status": "EMPTY",
        "downloaded": 0,
        "inserted": 0,
        "duplicates": 0,
        "omitted_trailing_count": 0,
        "omission_types": [],
        "failure_type": None,
    }

    with pytest.raises(ValueError, match="partial"):
        diagnostic().run(selection, checkpoint)


def test_rejects_negative_duration():
    selection, checkpoint, _ = schema4_evidence()

    with pytest.raises(ValueError, match="completed_at"):
        diagnostic(NOW, NOW - timedelta(seconds=1)).run(selection, checkpoint)

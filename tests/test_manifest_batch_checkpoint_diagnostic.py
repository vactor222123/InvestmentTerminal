from datetime import datetime, timezone

import pytest

from investment_terminal.operations.manifest_batch_checkpoint_diagnostic import (
    ManifestBatchCheckpointDiagnostic,
)
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.resumable_market_batch import (
    MarketBatchItem,
    MarketBatchRequest,
)


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def selection():
    request = MarketBatchRequest(
        resolution="D",
        start=NOW.replace(year=2016),
        end=NOW,
        items=(
            MarketBatchItem("AAA", "USD"),
            MarketBatchItem("BBB", "USD"),
            MarketBatchItem("CCC", "USD"),
        ),
    )
    return ManifestBatchSelection("a" * 64, 19, 601, request)


def checkpoint(request_checksum):
    return {
        "schema_version": 1,
        "request_checksum": request_checksum,
        "outcomes": {
            "AAA": {"status": "SUCCESS", "failure_type": None},
            "BBB": {"status": "EMPTY", "failure_type": None},
            "CCC": {
                "status": "FAILED",
                "failure_type": "YahooCandleInvalidResponseError",
            },
        },
    }


def test_reports_only_aggregate_bound_checkpoint_evidence():
    selected = selection()

    report = ManifestBatchCheckpointDiagnostic(clock=lambda: NOW).run(
        selected,
        checkpoint(selected.request.checksum),
    )

    assert report["status"] == "SUCCESS"
    assert report["batch_index"] == 19
    assert report["coverage"] == {
        "requested_count": 3,
        "success_count": 1,
        "empty_count": 1,
        "retryable_failure_count": 1,
        "final_failure_count": 0,
    }
    assert report["failure_types"] == ["YahooCandleInvalidResponseError"]
    assert all(symbol not in str(report) for symbol in ("AAA", "BBB", "CCC"))


def test_reports_final_failure_separately_from_retryable_failure():
    selected = selection()
    value = checkpoint(selected.request.checksum)
    value["schema_version"] = 3
    value["outcomes"]["CCC"].update({
        "status": "FINAL_FAILED",
        "downloaded": None,
        "inserted": None,
        "duplicates": None,
        "omitted_trailing_count": 0,
        "omission_types": [],
        "failure_category": "RESPONSE_NUMERIC",
        "isolation_policy_identity": (
            "NORMAL_AND_REPAIRED_STRICT_REJECTION_V1"
        ),
        "isolation_evidence": {
            "normal_diagnostic_checksum": "a" * 64,
            "repaired_qualification_checksum": "b" * 64,
        },
    })
    for key in ("AAA", "BBB"):
        value["outcomes"][key].update({
            "omitted_trailing_count": 0,
            "omission_types": [],
        })

    report = ManifestBatchCheckpointDiagnostic(clock=lambda: NOW).run(
        selected, value
    )

    assert report["schema_version"] == 2
    assert report["coverage"]["retryable_failure_count"] == 0
    assert report["coverage"]["final_failure_count"] == 1
    assert report["failure_types"] == []
    assert report["final_failure_categories"] == ["RESPONSE_NUMERIC"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(request_checksum="0" * 64),
        lambda value: value["outcomes"].pop("CCC"),
        lambda value: value["outcomes"].update(
            DDD={"status": "SUCCESS", "failure_type": None}
        ),
        lambda value: value["outcomes"]["CCC"].update(status="PENDING"),
        lambda value: value["outcomes"]["CCC"].update(failure_type=""),
        lambda value: value["outcomes"]["AAA"].update(failure_type="Unexpected"),
    ],
)
def test_rejects_unbound_or_invalid_checkpoint(mutate):
    selected = selection()
    value = checkpoint(selected.request.checksum)
    mutate(value)

    with pytest.raises(ValueError):
        ManifestBatchCheckpointDiagnostic(clock=lambda: NOW).run(selected, value)

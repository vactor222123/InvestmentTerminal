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
        "failure_count": 1,
    }
    assert report["failure_types"] == ["YahooCandleInvalidResponseError"]
    assert all(symbol not in str(report) for symbol in ("AAA", "BBB", "CCC"))


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

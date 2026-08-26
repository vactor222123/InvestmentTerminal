"""Synthetic tests for bounded OpenFIGI metadata bootstrap."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from investment_terminal.market.instrument_identity_models import InstrumentIdentity
from investment_terminal.portfolio.openfigi_metadata_bootstrap import (
    OpenFigiBootstrapFailure,
    OpenFigiHttpClient,
    OpenFigiFailureCategory,
    OpenFigiMetadataBootstrapService,
)
from investment_terminal.portfolio.portfolio_market_value_models import PortfolioPriceQuote
from investment_terminal.portfolio.portfolio_price_provider import InMemoryPortfolioPriceProvider
from investment_terminal.portfolio.position_reconstruction import PositionReconstruction, ReconstructedPosition

NOW = datetime(2026, 8, 26, 12, tzinfo=timezone.utc)


class Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def map_isins(self, isins):
        self.calls.append(isins)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def identity(index):
    return InstrumentIdentity(
        f"S{index}", f"Security {index}", "STOCK", "EUR",
        isin=f"DE00000000{index:02d}",
    )


def inputs(count=2):
    positions = tuple(
        ReconstructedPosition(identity(index), 1, 10, 10, "EUR")
        for index in range(1, count + 1)
    )
    reconstruction = PositionReconstruction("main", "Personal", count, positions)
    quotes = {
        item.instrument_key: PortfolioPriceQuote(
            item.instrument_key, f"T{index}", 11, "EUR", NOW, "PRIVATE"
        )
        for index, item in enumerate(positions, start=1)
    }
    return reconstruction, InMemoryPortfolioPriceProvider(quotes)


def response(*tickers):
    return json.dumps([
        {"data": [{"figi": f"FIGI-{ticker}", "ticker": ticker, "exchCode": "GY"}]}
        for ticker in tickers
    ], separators=(",", ":")).encode()


def run(tmp_path, client, *, count=2, batch_size=5):
    reconstruction, quotes = inputs(count)
    return OpenFigiMetadataBootstrapService(client, batch_size=batch_size).bootstrap(
        reconstruction, quotes, retrieved_at=NOW, run_id="run-1",
        archive_directory=tmp_path / "archive",
        metadata_output=tmp_path / "metadata.json",
    )


def test_bootstrap_batches_in_order_archives_exact_bytes_and_writes_metadata(tmp_path: Path):
    first = response("T1", "T2")
    second = response("T3")
    client = Client([first, second])
    result = run(tmp_path, client, count=3, batch_size=2)
    assert client.calls == [
        ("DE0000000001", "DE0000000002"),
        ("DE0000000003",),
    ]
    assert (result.requested_count, result.matched_count, result.batch_count,
            result.archived_response_count) == (3, 3, 2, 2)
    assert (tmp_path / "archive/run-1.batch-001.json").read_bytes() == first
    payload = json.loads((tmp_path / "metadata.json").read_text())
    assert payload["instruments"][0]["exchange_code"] is None
    assert payload["instruments"][0]["provenance"]["checksum_sha256"] == sha256(first).hexdigest()


def test_duplicate_same_ticker_rows_are_accepted_and_figis_preserved(tmp_path: Path):
    raw = json.dumps([{"data": [
        {"figi": "B", "ticker": "T1"}, {"figi": "A", "ticker": "T1"}
    ]}]).encode()
    result = run(tmp_path, Client([raw]), count=1)
    assert result.metadata.instruments[0].provenance.source_record_id == "A,B"


def test_alternative_listing_rows_are_ignored_after_candidate_confirmation(tmp_path: Path):
    raw = json.dumps([{"data": [
        {"figi": "CANDIDATE-B", "ticker": "T1"},
        {"figi": "ALTERNATIVE", "ticker": "OTHER"},
        {"figi": "CANDIDATE-A", "ticker": "T1"},
        {"ticker": "ANOTHER"},
    ]}]).encode()
    result = run(tmp_path, Client([raw]), count=1)
    assert result.metadata.instruments[0].provenance.source_record_id == (
        "CANDIDATE-A,CANDIDATE-B"
    )


@pytest.mark.parametrize(("raw", "category"), [
    (json.dumps([{"warning": "no match"}]).encode(), OpenFigiFailureCategory.PROVIDER_WARNING),
    (json.dumps([{"error": "bad job"}]).encode(), OpenFigiFailureCategory.PROVIDER_ERROR),
    (json.dumps([{"data": [{"figi": "A", "ticker": "OTHER"}]}]).encode(),
     OpenFigiFailureCategory.CANDIDATE_TICKER_ABSENT),
    (b"not-json", OpenFigiFailureCategory.RESPONSE_INVALID),
    (json.dumps([]).encode(), OpenFigiFailureCategory.RESPONSE_INVALID),
])
def test_failures_have_privacy_safe_category_after_archive(
    tmp_path: Path, raw: bytes, category: OpenFigiFailureCategory
):
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([raw]), count=1)
    assert captured.value.archived_response_count == 1
    assert captured.value.failure_category is category
    assert (tmp_path / "archive/run-1.batch-001.json").read_bytes() == raw
    assert not (tmp_path / "metadata.json").exists()


def test_transport_failure_preserves_previous_batch_archive(tmp_path: Path):
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([response("T1"), TimeoutError()]), count=2, batch_size=1)
    assert captured.value.archived_response_count == 1
    assert captured.value.batch_count == 2
    assert captured.value.failure_category is OpenFigiFailureCategory.PROVIDER_REQUEST_FAILED


def test_candidate_absence_carries_exact_private_diagnostic(tmp_path: Path):
    raw = json.dumps([{"data": [
        {"figi": "PRIVATE-FIGI", "ticker": "OTHER", "exchCode": "PRIVATE"},
        {"ticker": "other"},
        {"ticker": "SECOND"},
        {"ticker": ""},
    ]}], separators=(",", ":")).encode()
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([response("T1"), raw]), count=2, batch_size=1)
    diagnostic = captured.value.private_diagnostic
    assert diagnostic is not None
    assert diagnostic.to_dict() == {
        "schema_version": 1,
        "run_id": "run-1",
        "retrieved_at": NOW.isoformat(),
        "failure_category": "CANDIDATE_TICKER_ABSENT",
        "request_ordinal": 2,
        "batch_number": 2,
        "instrument_key": "DE0000000002",
        "candidate_ticker": "T2",
        "provider_tickers": ["OTHER", "SECOND"],
        "response_sha256": sha256(raw).hexdigest(),
    }
    diagnostic_text = json.dumps(diagnostic.to_dict())
    assert "PRIVATE-FIGI" not in diagnostic_text
    assert "exchCode" not in diagnostic_text
    assert "PRIVATE" not in diagnostic_text


def test_other_failure_has_no_private_diagnostic(tmp_path: Path):
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([b"not-json"]), count=1)
    assert captured.value.private_diagnostic is None


def test_existing_archive_fails_closed_without_replacement(tmp_path: Path):
    archive = tmp_path / "archive"
    archive.mkdir()
    existing = archive / "run-1.batch-001.json"
    existing.write_bytes(b"original")
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([response("T1")]), count=1)
    assert existing.read_bytes() == b"original"
    assert captured.value.failure_category is OpenFigiFailureCategory.RESPONSE_ARCHIVE_FAILED


def test_matching_ticker_without_figi_has_safe_category(tmp_path: Path):
    raw = json.dumps([{"data": [
        {"ticker": "T1"}, {"figi": "ALTERNATIVE", "ticker": "OTHER"}
    ]}]).encode()
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([raw]), count=1)
    assert captured.value.failure_category is OpenFigiFailureCategory.FIGI_MISSING


def test_metadata_write_failure_has_safe_category(tmp_path: Path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private path detail")

    monkeypatch.setattr(
        "investment_terminal.portfolio.openfigi_metadata_bootstrap.write_json_atomic",
        fail,
    )
    with pytest.raises(OpenFigiBootstrapFailure) as captured:
        run(tmp_path, Client([response("T1")]), count=1)
    assert captured.value.failure_category is OpenFigiFailureCategory.METADATA_WRITE_FAILED


def test_http_client_builds_v3_request_and_optional_api_key(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read(self): return b"[]"

    def urlopen(value, timeout):
        captured["request"] = value
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("investment_terminal.portfolio.openfigi_metadata_bootstrap.request.urlopen", urlopen)
    assert OpenFigiHttpClient(api_key="secret", timeout_seconds=4).map_isins(("DE0000000001",)) == b"[]"
    value = captured["request"]
    assert value.full_url == "https://api.openfigi.com/v3/mapping"
    assert value.get_header("X-openfigi-apikey") == "secret"
    assert json.loads(value.data) == [{"idType": "ID_ISIN", "idValue": "DE0000000001"}]
    assert captured["timeout"] == 4


def test_http_client_normalizes_network_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr("investment_terminal.portfolio.openfigi_metadata_bootstrap.request.urlopen", fail)
    with pytest.raises(RuntimeError, match="mapping request failed"):
        OpenFigiHttpClient().map_isins(("DE0000000001",))

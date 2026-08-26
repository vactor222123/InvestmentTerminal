"""Bounded OpenFIGI v3 bootstrap for private instrument metadata."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
from typing import Protocol
from urllib import error, request

from investment_terminal.market.market_metadata_quality import MarketMetadataProvenance
from investment_terminal.portfolio.instrument_metadata_enrichment import (
    InstrumentMetadataDocument,
    InstrumentMetadataEvidence,
)
from investment_terminal.portfolio.portfolio_price_provider import PortfolioPriceProvider
from investment_terminal.portfolio.position_reconstruction import PositionReconstruction
from investment_terminal.utils.atomic_write import write_json_atomic
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class OpenFigiMappingClient(Protocol):
    def map_isins(self, isins: tuple[str, ...]) -> bytes: ...


class OpenFigiHttpClient:
    """Small synchronous adapter for the documented OpenFIGI v3 endpoint."""

    URL = "https://api.openfigi.com/v3/mapping"

    def __init__(self, *, api_key: str | None = None, timeout_seconds: float = 30) -> None:
        self.api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self.timeout_seconds = float(timeout_seconds)

    def map_isins(self, isins: tuple[str, ...]) -> bytes:
        if not isins or len(isins) > (100 if self.api_key else 5):
            raise ValueError("OpenFIGI mapping batch size is invalid")
        body = json.dumps(
            [{"idType": "ID_ISIN", "idValue": value} for value in isins],
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key is not None:
            headers["X-OPENFIGI-APIKEY"] = self.api_key
        value = request.Request(self.URL, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(value, timeout=self.timeout_seconds) as response:
                return response.read()
        except (error.HTTPError, error.URLError, socket.timeout, TimeoutError) as exc:
            raise RuntimeError("OpenFIGI mapping request failed") from exc


@dataclass(frozen=True, slots=True)
class OpenFigiBootstrapResult:
    requested_count: int
    matched_count: int
    batch_count: int
    archived_response_count: int
    metadata: InstrumentMetadataDocument


class OpenFigiBootstrapFailure(RuntimeError):
    def __init__(self, message: str, *, requested_count: int,
                 batch_count: int, archived_response_count: int) -> None:
        super().__init__(message)
        self.requested_count = requested_count
        self.batch_count = batch_count
        self.archived_response_count = archived_response_count


class OpenFigiMetadataBootstrapService:
    """Confirm quote tickers against OpenFIGI and publish reusable evidence."""

    def __init__(self, client: OpenFigiMappingClient, *, batch_size: int = 5) -> None:
        if not isinstance(batch_size, int) or not 1 <= batch_size <= 100:
            raise ValueError("batch_size must be between 1 and 100")
        self.client = client
        self.batch_size = batch_size

    def bootstrap(self, reconstruction: PositionReconstruction,
                  price_provider: PortfolioPriceProvider, *, retrieved_at: datetime,
                  run_id: str, archive_directory: str | Path,
                  metadata_output: str | Path) -> OpenFigiBootstrapResult:
        if not isinstance(reconstruction, PositionReconstruction):
            raise TypeError("reconstruction must be PositionReconstruction")
        observed = validate_aware_datetime(retrieved_at, field_name="retrieved_at")
        normalized_run = normalize_required_text(run_id, field_name="run_id")
        if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in normalized_run):
            raise ValueError("run_id contains unsupported characters")
        positions = reconstruction.positions
        requested_count = len(positions)
        if not positions:
            raise ValueError("OpenFIGI bootstrap requires open positions")
        keys = {item.instrument_key for item in positions}
        if set(price_provider.instrument_keys) != keys:
            raise ValueError("quote coverage must exactly match open positions")
        for item in positions:
            if item.instrument.isin is None or item.instrument_key != item.instrument.isin:
                raise ValueError("OpenFIGI bootstrap requires ISIN-keyed open positions")

        batches = tuple(
            positions[index:index + self.batch_size]
            for index in range(0, len(positions), self.batch_size)
        )
        archive_root = Path(archive_directory)
        evidence: list[InstrumentMetadataEvidence] = []
        archived = 0
        try:
            for batch_number, batch in enumerate(batches, start=1):
                raw = self.client.map_isins(tuple(item.instrument_key for item in batch))
                if not isinstance(raw, bytes):
                    raise TypeError("OpenFIGI client must return bytes")
                archive_root.mkdir(parents=True, exist_ok=True)
                archive_path = archive_root / f"{normalized_run}.batch-{batch_number:03d}.json"
                with archive_path.open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                archived += 1
                checksum = sha256(raw).hexdigest()
                responses = self._responses(raw, expected=len(batch))
                for position, response in zip(batch, responses, strict=True):
                    candidates = {
                        quote.instrument_key: quote
                        for quote in price_provider.quotes
                    }
                    quote = candidates[position.instrument_key]
                    rows = self._rows(response)
                    tickers = {
                        str(row.get("ticker", "")).strip().upper()
                        for row in rows if str(row.get("ticker", "")).strip()
                    }
                    if tickers != {quote.exchange_ticker}:
                        raise ValueError("OpenFIGI ticker result is missing or ambiguous")
                    figis = sorted({str(row.get("figi", "")).strip() for row in rows
                                    if str(row.get("ticker", "")).strip().upper() == quote.exchange_ticker
                                    and str(row.get("figi", "")).strip()})
                    if not figis:
                        raise ValueError("OpenFIGI matching rows contain no FIGI")
                    evidence.append(InstrumentMetadataEvidence(
                        instrument_key=position.instrument_key,
                        exchange_ticker=quote.exchange_ticker,
                        exchange_code=None,
                        provenance=MarketMetadataProvenance(
                            source="OPENFIGI_V3",
                            source_record_id=",".join(figis),
                            observed_at=observed,
                            fetched_at=observed,
                            checksum_sha256=checksum,
                        ),
                    ))
            document = InstrumentMetadataDocument(tuple(sorted(evidence, key=lambda item: item.instrument_key)))
            write_json_atomic(metadata_output, document.to_dict(), ensure_ascii=False)
            return OpenFigiBootstrapResult(requested_count, len(evidence), len(batches), archived, document)
        except Exception as exc:
            raise OpenFigiBootstrapFailure(
                "OpenFIGI metadata bootstrap failed",
                requested_count=requested_count,
                batch_count=len(batches),
                archived_response_count=archived,
            ) from exc

    @staticmethod
    def _responses(raw: bytes, *, expected: int) -> list[object]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("OpenFIGI response is invalid JSON") from exc
        if not isinstance(payload, list) or len(payload) != expected:
            raise ValueError("OpenFIGI response does not align with request")
        return payload

    @staticmethod
    def _rows(response: object) -> list[dict[str, object]]:
        if not isinstance(response, dict) or "error" in response or "warning" in response:
            raise ValueError("OpenFIGI mapping result is unavailable")
        rows = response.get("data")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("OpenFIGI mapping data is malformed")
        return rows


def bootstrap_report(*, status: str, started_at: datetime, completed_at: datetime,
                     requested_count: int | None, matched_count: int | None,
                     batch_count: int | None, archived_response_count: int | None,
                     failure_type: str | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": (completed_at - started_at).total_seconds(),
        "coverage": {
            "requested_count": requested_count,
            "matched_count": matched_count,
            "batch_count": batch_count,
            "archived_response_count": archived_response_count,
        },
        "failure": None if failure_type is None else {
            "type": failure_type, "reason": "OpenFIGI metadata bootstrap failed"
        },
        "limitations": [
            "report excludes paths, ISINs, tickers, FIGIs, response bodies, and credentials",
            "provider exchange codes are not projected as MICs",
            "bootstrap does not qualify quotes, value the portfolio, or mutate transactions",
        ],
    }

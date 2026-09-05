"""Construct private deterministic market-batch requests from qualified evidence."""

from datetime import datetime
from hashlib import sha256
import json

from investment_terminal.operations.resumable_market_batch import MarketBatchRequest
from investment_terminal.operations.symbol_currency_qualification import (
    SymbolCurrencyQualificationService,
    _checksum,
)
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class MarketBatchManifestService:
    """Join success projection and complete currency evidence without I/O."""

    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        projection: object,
        projection_checksum: str,
        currency_checkpoint: object,
        *,
        resolution: str,
        start: datetime,
        end: datetime,
    ) -> tuple[dict[str, object], dict[str, object]]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        symbols, actual_projection_checksum = (
            SymbolCurrencyQualificationService._projection(projection)
        )
        expected_projection_checksum = normalize_required_text(
            projection_checksum,
            field_name="projection_checksum",
        ).lower()
        if expected_projection_checksum != actual_projection_checksum:
            raise ValueError("Projection checksum does not match")

        currency_request_checksum = _checksum({
            "schema_version": 2,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "projection_checksum": actual_projection_checksum,
        })
        if (
            not isinstance(currency_checkpoint, dict)
            or currency_checkpoint.get("schema_version") != 2
        ):
            raise ValueError(
                "Market batch manifest requires schema-version-2 currency evidence"
            )
        outcomes, migrated = SymbolCurrencyQualificationService._outcomes(
            currency_checkpoint,
            currency_request_checksum,
            actual_projection_checksum,
        )
        if migrated:
            raise ValueError("Market batch manifest requires schema-version-2 currency evidence")
        if set(outcomes) != set(symbols):
            raise ValueError("Currency checkpoint symbol set does not match projection")
        if any(
            item.get("status") not in {"SUCCESS", "FINAL_FAILED"}
            for item in outcomes.values()
        ):
            raise ValueError("Currency checkpoint is not complete")

        items = []
        excluded_categories: dict[str, int] = {}
        for symbol in symbols:
            outcome = outcomes[symbol]
            if outcome["status"] == "FINAL_FAILED":
                category = normalize_required_text(
                    outcome.get("failure_category"),
                    field_name="failure_category",
                    uppercase=True,
                )
                excluded_categories[category] = excluded_categories.get(category, 0) + 1
                continue
            currency = normalize_required_text(
                outcome.get("currency"), field_name="currency", uppercase=True
            )
            if len(currency) != 3 or not currency.isalpha():
                raise ValueError("Successful currency must be a three-letter code")
            items.append({"symbol": symbol, "currency": currency})
        if not items:
            raise ValueError("Market batch manifest requires at least one successful item")

        batches = []
        for offset in range(0, len(items), 20):
            request = MarketBatchRequest.from_dict({
                "schema_version": 1,
                "resolution": resolution,
                "start": validate_aware_datetime(start, field_name="start").isoformat(),
                "end": validate_aware_datetime(end, field_name="end").isoformat(),
                "items": items[offset:offset + 20],
            })
            batches.append({
                "batch_index": len(batches) + 1,
                "request_checksum": request.checksum,
                "request": request.canonical_dict(),
            })

        manifest = {
            "schema_version": 1,
            "manifest_identity": "QUALIFIED_MARKET_BATCH_MANIFEST",
            "projection_checksum": actual_projection_checksum,
            "currency_request_checksum": currency_request_checksum,
            "batches": batches,
        }
        manifest_checksum = _manifest_checksum(manifest)
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        report = {
            "schema_version": 1,
            "operation_identity": "MARKET_BATCH_MANIFEST_CONSTRUCTION",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "projection_checksum": actual_projection_checksum,
            "currency_request_checksum": currency_request_checksum,
            "manifest_checksum": manifest_checksum,
            "coverage": {
                "member_count": len(symbols),
                "included_count": len(items),
                "excluded_count": len(symbols) - len(items),
                "batch_count": len(batches),
                "maximum_batch_size": 20,
                "minimum_batch_size": min(len(batch["request"]["items"]) for batch in batches),
                "excluded_categories": dict(sorted(excluded_categories.items())),
            },
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, paths, prices, and provider text",
                "manifest construction does not contact providers, ingest candles, schedule work, analyze, or trade",
            ],
        }
        return manifest, report


def _manifest_checksum(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return sha256(raw.encode("utf-8")).hexdigest()

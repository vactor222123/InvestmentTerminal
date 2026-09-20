"""CLI for one evidence-bound retry of a partial manifest timeout."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_finance_client import YahooFinanceClient
from investment_terminal.database.database import Database
from investment_terminal.operations.manifest_bound_market_batch import (
    ManifestBatchSelection,
)
from investment_terminal.operations.manifest_partial_timeout_retry import (
    ManifestPartialTimeoutRetryService,
    prepare_partial_timeout_retry,
)
from investment_terminal.operations.manifest_terminal_series_isolation import (
    _reject_constant,
    _unique_object,
)
from investment_terminal.repositories.candle_repository import CandleRepository
from investment_terminal.services.projected_historical_market_service import (
    ProjectedHistoricalMarketService,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Retry one inventory-bound timeout in a partial batch."
    )
    value.add_argument("--manifest", type=Path, required=True)
    value.add_argument("--manifest-checksum", required=True)
    value.add_argument("--batch-index", type=int, required=True)
    value.add_argument("--checkpoint", type=Path, required=True)
    value.add_argument("--inventory", type=Path, required=True)
    value.add_argument("--inventory-checksum", required=True)
    value.add_argument("--database", type=Path, required=True)
    value.add_argument("--cache-directory", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(
    argv: Sequence[str] | None = None,
    *,
    client=None,
    clock=None,
    checkpoint_writer=write_json_atomic,
    report_writer=write_json_atomic,
) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    database = None
    selection = None
    inventory_bytes = b""
    try:
        manifest = _strict_json_file(options.manifest)
        selection = ManifestBatchSelection.from_manifest(
            manifest,
            options.manifest_checksum,
            options.batch_index,
        )
        checkpoint = _strict_json_file(options.checkpoint)
        inventory_bytes = options.inventory.read_bytes()
        prepare_partial_timeout_retry(
            selection,
            checkpoint,
            inventory_bytes=inventory_bytes,
            inventory_checksum=options.inventory_checksum,
        )
        database = Database(options.database)
        database.initialize()
        importer = ProjectedHistoricalMarketService(
            client or YahooFinanceClient(cache_directory=options.cache_directory),
            CandleRepository(database),
        )
        updated, payload = ManifestPartialTimeoutRetryService(
            importer=importer,
            clock=runtime_clock,
        ).run(
            selection,
            checkpoint,
            inventory_bytes=inventory_bytes,
            inventory_checksum=options.inventory_checksum,
        )
    except Exception:
        payload = _failed_payload(
            selection,
            runtime_clock(),
            "VALIDATION_OR_IO_ERROR",
        )
        report_writer(options.report_output, payload)
        if options.json:
            print(json.dumps(payload, indent=2, allow_nan=False))
        if database is not None:
            database.close()
        return 1
    try:
        checkpoint_writer(options.checkpoint, updated)
    except Exception:
        payload = _failed_payload(
            selection,
            runtime_clock(),
            "CHECKPOINT_WRITE_FAILED",
        )
        report_writer(options.report_output, payload)
        if options.json:
            print(json.dumps(payload, indent=2, allow_nan=False))
        return 1
    finally:
        if database is not None:
            database.close()

    report_writer(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["status"] == "READY_FOR_SWEEP" else 1


def _strict_json_file(path: Path) -> object:
    try:
        return json.loads(
            path.read_bytes().decode("utf-8"),
            parse_constant=lambda value: _reject_constant(value),
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Input must contain strict UTF-8 JSON") from exc


def _failed_payload(
    selection: ManifestBatchSelection | None,
    now: datetime,
    category: str,
) -> dict[str, object]:
    bound = selection is not None
    return {
        "schema_version": 1,
        "operation_identity": "MANIFEST_PARTIAL_TIMEOUT_RETRY",
        "provider_identity": "YAHOO_FINANCE",
        "status": "FAILED",
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "duration_seconds": 0.0,
        "manifest_checksum": selection.manifest_checksum if bound else None,
        "batch_index": selection.batch_index if bound else None,
        "batch_count": selection.batch_count if bound else None,
        "request_checksum": selection.request.checksum if bound else None,
        "requested_start": selection.request.start.isoformat() if bound else None,
        "requested_end": selection.request.end.isoformat() if bound else None,
        "inventory_checksum": None,
        "coverage": None,
        "retry_result": None,
        "failure": {
            "category": category,
            "reason": "Manifest partial timeout retry failed",
        },
        "limitations": [
            "failed report excludes private values, paths, provider text, and exception messages"
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())

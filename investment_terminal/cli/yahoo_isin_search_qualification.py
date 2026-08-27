"""CLI for bounded private Yahoo ISIN-search qualification."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.clients.yahoo_search_client import YahooSearchClient
from investment_terminal.operations.yahoo_isin_search_qualification import (
    YahooIsinSearchQualification,
    YahooIsinSearchQualificationService,
    YahooIsinSearchStatus,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Qualify one private Yahoo ISIN search.")
    value.add_argument("--candidate-diagnostic", type=Path, required=True)
    value.add_argument("--private-candidates-output", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--timeout-seconds", type=float, default=30.0)
    value.add_argument("--json", action="store_true")
    return value


def main(argv: Sequence[str] | None = None, *, client=None, clock=None) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        diagnostic = json.loads(options.candidate_diagnostic.read_text(encoding="utf-8"))
        if diagnostic.get("schema_version") != 1:
            raise ValueError("Unsupported candidate diagnostic schema")
        if diagnostic.get("failure_category") != "CANDIDATE_TICKER_ABSENT":
            raise ValueError("Candidate diagnostic category is invalid")
        isin = diagnostic["instrument_key"]
        result = YahooIsinSearchQualificationService(
            client=client or YahooSearchClient(timeout_seconds=options.timeout_seconds),
            clock=runtime_clock,
        ).qualify(isin)
        if result.status is not YahooIsinSearchStatus.FAILED:
            write_json_atomic(options.private_candidates_output, result.private_dict())
    except Exception as exc:
        started = runtime_clock()
        result = YahooIsinSearchQualification(
            YahooIsinSearchStatus.FAILED, started, started, (), type(exc).__name__
        )
    payload = result.report_dict()
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print(f"Yahoo ISIN Search Qualification: {result.status.value}")
    return 0 if result.status is not YahooIsinSearchStatus.FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())

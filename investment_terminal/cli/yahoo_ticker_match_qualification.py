"""CLI for private exact-ticker qualification against Yahoo ISIN candidates."""

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path

from investment_terminal.operations.yahoo_ticker_match_qualification import (
    YahooTickerMatchQualification,
    YahooTickerMatchQualificationService,
    YahooTickerMatchStatus,
)
from investment_terminal.utils.atomic_write import write_json_atomic


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Qualify one existing ticker against Yahoo ISIN candidates.")
    value.add_argument("--candidate-diagnostic", type=Path, required=True)
    value.add_argument("--private-candidates", type=Path, required=True)
    value.add_argument("--quotes", type=Path, required=True)
    value.add_argument("--private-match-output", type=Path, required=True)
    value.add_argument("--report-output", type=Path, required=True)
    value.add_argument("--json", action="store_true")
    return value


def main(argv: Sequence[str] | None = None, *, clock=None) -> int:
    options = parser().parse_args(argv)
    runtime_clock = clock or (lambda: datetime.now(timezone.utc))
    try:
        diagnostic = json.loads(options.candidate_diagnostic.read_text(encoding="utf-8"))
        candidate_doc = json.loads(options.private_candidates.read_text(encoding="utf-8"))
        quote_doc = json.loads(options.quotes.read_text(encoding="utf-8"))
        if diagnostic.get("schema_version") != 1 or diagnostic.get("failure_category") != "CANDIDATE_TICKER_ABSENT":
            raise ValueError("Candidate diagnostic is invalid")
        if candidate_doc.get("schema_version") != 1 or candidate_doc.get("provider_identity") != "YAHOO_FINANCE_SEARCH":
            raise ValueError("Yahoo candidate document is invalid")
        key = diagnostic["instrument_key"]
        quotes = quote_doc.get("quotes")
        if not isinstance(quotes, list):
            raise ValueError("Quote document is invalid")
        matching_quotes = [item for item in quotes if isinstance(item, dict) and item.get("instrument_key") == key]
        if len(matching_quotes) != 1:
            raise ValueError("Exactly one quote must match the diagnostic instrument")
        result = YahooTickerMatchQualificationService(clock=runtime_clock).qualify(
            instrument_key=key,
            exchange_ticker=matching_quotes[0].get("exchange_ticker"),
            candidates=candidate_doc.get("candidates"),
        )
        if result.status is YahooTickerMatchStatus.MATCHED:
            write_json_atomic(options.private_match_output, result.private_match)
    except Exception as exc:
        started = runtime_clock()
        result = YahooTickerMatchQualification(
            YahooTickerMatchStatus.FAILED, started, started, None, None,
            failure_type=type(exc).__name__,
        )
    payload = result.report_dict()
    write_json_atomic(options.report_output, payload)
    if options.json:
        print(json.dumps(payload, indent=2, allow_nan=False))
    else:
        print(f"Yahoo Ticker Match Qualification: {result.status.value}")
    return 0 if result.status is YahooTickerMatchStatus.MATCHED else 1


if __name__ == "__main__":
    raise SystemExit(main())

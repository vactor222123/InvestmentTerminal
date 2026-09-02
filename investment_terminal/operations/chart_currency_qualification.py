"""One-symbol chart-metadata currency qualification."""

from investment_terminal.operations.symbol_currency_qualification import (
    SymbolCurrencyQualificationService,
    _checksum,
)
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class ChartCurrencyQualificationService:
    def __init__(self, *, client, clock) -> None:
        self.client = client
        self.clock = clock

    def run(self, projection: object, projection_checksum: str, checkpoint: object):
        symbols, actual = SymbolCurrencyQualificationService._projection(projection)
        if normalize_required_text(projection_checksum, field_name="projection_checksum").lower() != actual:
            raise ValueError("Projection checksum does not match")
        request_checksum = _checksum({"schema_version": 1,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "projection_checksum": actual})
        outcomes = SymbolCurrencyQualificationService._outcomes(
            checkpoint, request_checksum, actual)
        candidates = sorted(symbol for symbol in symbols
            if outcomes.get(symbol, {}).get("status") == "FINAL_FAILED"
            and outcomes[symbol].get("failure_category") == "INVALID_CURRENCY")
        if not candidates:
            raise ValueError("No terminal invalid-currency outcome is available")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        currency = self.client.get_currency(candidates[0])
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        private = {"schema_version": 1,
                   "evidence_identity": "YAHOO_CHART_CURRENCY_QUALIFICATION",
                   "projection_checksum": actual,
                   "qualification_request_checksum": request_checksum,
                   "symbol": candidates[0], "currency": currency}
        evidence_checksum = _checksum(private)
        report = {"schema_version": 1,
                  "operation_identity": "YAHOO_CHART_CURRENCY_QUALIFICATION",
                  "provider_identity": "YAHOO_FINANCE_CHART_METADATA",
                  "status": "SUCCESS", "started_at": started.isoformat(),
                  "completed_at": completed.isoformat(),
                  "duration_seconds": (completed-started).total_seconds(),
                  "projection_checksum": actual,
                  "qualification_request_checksum": request_checksum,
                  "evidence_checksum": evidence_checksum,
                  "coverage": {"attempted_count": 1, "qualified_count": 1},
                  "failure": None,
                  "limitations": ["report excludes symbols, currency values, paths, provider text, and exception messages",
                                  "qualification does not mutate checkpoints, expand scans, generate batches, or ingest data"]}
        return private, report

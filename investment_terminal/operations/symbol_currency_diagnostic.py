"""Privacy-safe diagnostic for one terminal invalid-currency outcome."""

from datetime import datetime

from investment_terminal.operations.symbol_currency_qualification import (
    SymbolCurrencyQualificationService,
    _checksum,
)
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


class SymbolCurrencyDiagnosticService:
    def __init__(self, *, client, clock) -> None:
        self.client = client
        self.clock = clock

    def run(self, projection: object, projection_checksum: str, checkpoint: object):
        symbols, actual = SymbolCurrencyQualificationService._projection(projection)
        expected = normalize_required_text(
            projection_checksum, field_name="projection_checksum"
        ).lower()
        if expected != actual:
            raise ValueError("Projection checksum does not match")
        request_checksum = _checksum({
            "schema_version": 1,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "projection_checksum": actual,
        })
        outcomes = SymbolCurrencyQualificationService._outcomes(
            checkpoint, request_checksum, actual
        )
        candidates = sorted(
            symbol for symbol in symbols
            if outcomes.get(symbol, {}).get("status") == "FINAL_FAILED"
            and outcomes[symbol].get("failure_category") == "INVALID_CURRENCY"
        )
        if not candidates:
            raise ValueError("No terminal invalid-currency outcome is available")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        rows = self.client.search_symbol(candidates[0])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise TypeError("Yahoo search result must contain objects")
        shapes = {key: 0 for key in (
            "missing", "null", "empty", "non_string", "invalid_format", "valid_format"
        )}
        exact = 0
        valid_values = set()
        for row in rows:
            value = row.get("symbol")
            if not isinstance(value, str) or value.strip().upper() != candidates[0]:
                continue
            exact += 1
            if "currency" not in row:
                shapes["missing"] += 1
                continue
            currency = row["currency"]
            if currency is None:
                shapes["null"] += 1
            elif not isinstance(currency, str):
                shapes["non_string"] += 1
            elif not currency.strip():
                shapes["empty"] += 1
            else:
                normalized = currency.strip().upper()
                if len(normalized) == 3 and normalized.isalpha():
                    shapes["valid_format"] += 1
                    valid_values.add(normalized)
                else:
                    shapes["invalid_format"] += 1
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        return {
            "schema_version": 1,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_DIAGNOSTIC",
            "provider_identity": "YAHOO_FINANCE_SEARCH",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "projection_checksum": actual,
            "qualification_request_checksum": request_checksum,
            "coverage": {"result_count": len(rows), "exact_match_count": exact,
                         "currency_field_shapes": shapes,
                         "distinct_valid_currency_count": len(valid_values)},
            "failure": None,
            "limitations": ["report excludes symbols, currency values, paths, provider text, and exception messages",
                            "diagnostic is read-only and does not change qualification evidence"],
        }

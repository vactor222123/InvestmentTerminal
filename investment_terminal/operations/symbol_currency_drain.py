"""Budgeted coordinator for complete resumable symbol-currency qualification."""

from investment_terminal.operations.symbol_currency_qualification import (
    SymbolCurrencyQualificationService,
    _checksum,
)
from investment_terminal.utils.validation import validate_aware_datetime


class SymbolCurrencyDrainService:
    """Repeat unchanged currency slices until a durable stopping condition."""

    def __init__(self, *, client, checkpoint_writer, clock) -> None:
        self.client = client
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(
        self,
        projection: object,
        projection_checksum: str,
        checkpoint: object | None = None,
        *,
        max_total_items: int,
    ) -> dict[str, object]:
        if isinstance(max_total_items, bool) or not isinstance(max_total_items, int):
            raise TypeError("max_total_items must be an integer")
        if not 1 <= max_total_items <= 20000:
            raise ValueError("max_total_items must be between 1 and 20000")

        symbols, actual_checksum = SymbolCurrencyQualificationService._projection(
            projection
        )
        request_checksum = _checksum({
            "schema_version": 2,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_QUALIFICATION",
            "projection_checksum": actual_checksum,
        })
        outcomes, _ = SymbolCurrencyQualificationService._outcomes(
            checkpoint, request_checksum, actual_checksum
        )
        starting = self._coverage(len(symbols), outcomes)
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        current = checkpoint
        slices = attempted = provider_requests = 0

        def write(payload):
            nonlocal current
            self.checkpoint_writer(payload)
            current = payload

        service = SymbolCurrencyQualificationService(
            client=self.client,
            checkpoint_writer=write,
            clock=self.clock,
        )
        while attempted < max_total_items:
            report = service.run(
                projection,
                projection_checksum,
                current,
                max_items=min(100, max_total_items - attempted),
            )
            run_attempted = report["coverage"]["attempted_count"]
            slices += 1
            attempted += run_attempted
            provider_requests += run_attempted
            if report["status"] in {"COMPLETE", "HALTED"}:
                break
            if run_attempted == 0:
                raise RuntimeError("Symbol currency drain made zero progress")

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        status = (
            report["status"]
            if report["status"] in {"COMPLETE", "HALTED"}
            else "BUDGET_EXHAUSTED"
        )
        return {
            "schema_version": 1,
            "operation_identity": "YAHOO_SYMBOL_CURRENCY_DRAIN",
            "provider_identity": "YAHOO_FINANCE_CHART_METADATA",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "request_checksum": request_checksum,
            "projection_checksum": actual_checksum,
            "budget": {"max_total_items": max_total_items, "slice_size": 100},
            "current_run": {
                "slice_count": slices,
                "attempted_count": attempted,
                "provider_request_count": provider_requests,
            },
            "starting_coverage": starting,
            "ending_coverage": dict(report["coverage"]),
            "halt_category": report["halt_category"],
            "failure_categories": list(report["failure_categories"]),
            "failure": None,
            "limitations": [
                "report excludes symbols, currencies, paths, provider text, and exception messages",
                "currency completion does not generate batches, retrieve candles, or ingest data",
            ],
        }

    @staticmethod
    def _coverage(member_count: int, outcomes: dict[str, dict[str, object]]):
        values = list(outcomes.values())
        return {
            "member_count": member_count,
            "success_count": sum(item.get("status") == "SUCCESS" for item in values),
            "final_failure_count": sum(
                item.get("status") == "FINAL_FAILED" for item in values
            ),
            "retry_pending_count": sum(
                item.get("status") == "RETRY_PENDING" for item in values
            ),
            "never_attempted_count": member_count - len(outcomes),
        }

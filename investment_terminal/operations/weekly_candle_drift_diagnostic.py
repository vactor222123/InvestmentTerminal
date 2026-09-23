"""Read-only diagnosis of one checkpointed weekly candle drift."""

from collections import Counter
from investment_terminal.clients.yahoo_finance_client import (
    project_yahoo_candle_failure,
)
from investment_terminal.operations.weekly_candle_refresh import (
    WeeklyCandleRefreshPlan,
    _MAX_WINDOW,
    _OVERLAP,
    _validated_outcomes,
)
from investment_terminal.utils.validation import validate_aware_datetime


_FIELDS = (
    "open_price", "high_price", "low_price", "close_price", "volume", "currency"
)


class WeeklyCandleDriftDiagnosticService:
    """Compare one private failed series without changing candle storage."""

    def __init__(self, *, client, repository, clock):
        self.client = client
        self.repository = repository
        self.clock = clock

    def run(self, plan, checkpoint):
        if not isinstance(plan, WeeklyCandleRefreshPlan):
            raise TypeError("plan must be a WeeklyCandleRefreshPlan")
        outcomes = _validated_outcomes(checkpoint, plan)
        selected = [
            (symbol, currency) for symbol, currency in plan.items
            if symbol in outcomes
            and outcomes[symbol]["status"] == "FAILED"
            and outcomes[symbol]["category"] == "STORED_CANDLE_DRIFT"
        ]
        if not selected:
            raise ValueError("No checkpointed stored-candle drift exists")
        symbol, currency = selected[0]
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        latest = self.repository.get_latest(symbol, "D")
        if latest is None or latest.currency != currency:
            raise ValueError("Stored series no longer matches the selected identity")
        start = latest.timestamp - _OVERLAP
        if start >= plan.end or plan.end - start > _MAX_WINDOW:
            raise ValueError("Diagnostic window no longer matches refresh bounds")
        existing = {
            candle.timestamp: candle
            for candle in self.repository.get_range(symbol, "D", start, plan.end)
        }
        if not existing:
            raise ValueError("Stored overlap is empty")

        failure_category = None
        try:
            projection = self.client.get_candle_projection(
                symbol=symbol, resolution="D", start=start, end=plan.end,
                currency=currency, allow_trailing_incomplete=True,
            )
        except Exception as exc:
            failure_category = project_yahoo_candle_failure(exc).category.value
            projection = None

        field_counts = Counter()
        changed_rows = overlap_rows = new_rows = 0
        omitted = 0
        if projection is not None:
            omitted = projection.omitted_trailing_count
            for candle in projection.candles:
                if (
                    candle.symbol != symbol or candle.resolution != "D"
                    or candle.currency != currency
                    or not start <= candle.timestamp < plan.end
                ):
                    raise ValueError("Provider projection is outside the request")
                previous = existing.get(candle.timestamp)
                if previous is None:
                    new_rows += 1
                    continue
                overlap_rows += 1
                changed = [
                    field for field in _FIELDS
                    if getattr(previous, field) != getattr(candle, field)
                ]
                if changed:
                    changed_rows += 1
                    field_counts.update(changed)

        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        if completed < started:
            raise ValueError("completed_at is before started_at")
        status = (
            "PROVIDER_FAILURE" if failure_category else
            "INCONCLUSIVE" if not overlap_rows else
            "REPRODUCED" if changed_rows else "NOT_REPRODUCED"
        )
        return {
            "schema_version": 1,
            "operation_identity": "WEEKLY_CANDLE_DRIFT_DIAGNOSTIC",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "manifest_checksum": plan.manifest_checksum,
            "end": plan.end.isoformat(),
            "selection_checksum": plan.selection_checksum,
            "source_drift_count": len(selected),
            "overlap_count": overlap_rows,
            "changed_overlap_count": changed_rows,
            "new_candle_count": new_rows,
            "omitted_trailing_count": omitted,
            "changed_fields": [
                {"field": field, "count": count}
                for field, count in sorted(field_counts.items())
            ],
            "failure_category": failure_category,
            "failure": None,
            "limitations": [
                "one current provider response cannot establish the cause of earlier drift",
                "report excludes identities, prices, currencies, paths, timestamps, provider text, and exception messages",
                "diagnostic does not write candles or checkpoints",
            ],
        }

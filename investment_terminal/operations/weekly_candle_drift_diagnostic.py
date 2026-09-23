"""Read-only diagnosis of checkpointed weekly candle drift."""

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

    def run(self, plan, checkpoint, *, selection_index=0):
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
        if isinstance(selection_index, bool) or not isinstance(selection_index, int):
            raise TypeError("selection_index must be an integer")
        if not 0 <= selection_index < len(selected):
            raise ValueError("selection_index is outside the drift cohort")
        symbol, currency = selected[selection_index]
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


class WeeklyCandleDriftAggregateService:
    """Aggregate a bounded full drift cohort without identity-level output."""

    def __init__(self, *, client, repository, clock):
        self.single = WeeklyCandleDriftDiagnosticService(
            client=client, repository=repository, clock=clock
        )
        self.clock = clock

    def run(self, plan, checkpoint, *, max_items):
        if not isinstance(plan, WeeklyCandleRefreshPlan):
            raise TypeError("plan must be a WeeklyCandleRefreshPlan")
        outcomes = _validated_outcomes(checkpoint, plan)
        drift_count = sum(
            symbol in outcomes
            and outcomes[symbol]["status"] == "FAILED"
            and outcomes[symbol]["category"] == "STORED_CANDLE_DRIFT"
            for symbol, _ in plan.items
        )
        if not 1 <= drift_count <= 20:
            raise ValueError("Full drift cohort must contain one to twenty items")
        if isinstance(max_items, bool) or max_items != drift_count:
            raise ValueError("max_items must equal the full drift cohort")

        started = validate_aware_datetime(self.clock(), field_name="started_at")
        results = []
        for index in range(drift_count):
            result = self.single.run(plan, checkpoint, selection_index=index)
            results.append(result)
            if result["failure_category"] == "RATE_LIMITED":
                break
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        if completed < started:
            raise ValueError("completed_at is before started_at")

        statuses = Counter(result["status"] for result in results)
        fields = Counter()
        failure_categories = Counter()
        for result in results:
            fields.update({
                item["field"]: item["count"] for item in result["changed_fields"]
            })
            if result["failure_category"] is not None:
                failure_categories[result["failure_category"]] += 1
        volume_only = sum(
            result["status"] == "REPRODUCED"
            and len(result["changed_fields"]) == 1
            and result["changed_fields"][0]["field"] == "volume"
            for result in results
        )
        remaining = drift_count - len(results)
        status = (
            "HALTED" if failure_categories["RATE_LIMITED"] else
            "COMPLETE_WITH_PROVIDER_FAILURES" if statuses["PROVIDER_FAILURE"] else
            "COMPLETE"
        )
        return {
            "schema_version": 2,
            "operation_identity": "WEEKLY_CANDLE_DRIFT_DIAGNOSTIC",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "manifest_checksum": plan.manifest_checksum,
            "end": plan.end.isoformat(),
            "selection_checksum": plan.selection_checksum,
            "source_drift_count": drift_count,
            "attempted_count": len(results),
            "remaining_count": remaining,
            "reproduced_count": statuses["REPRODUCED"],
            "not_reproduced_count": statuses["NOT_REPRODUCED"],
            "inconclusive_count": statuses["INCONCLUSIVE"],
            "provider_failure_count": statuses["PROVIDER_FAILURE"],
            "volume_only_count": volume_only,
            "non_volume_only_drift_count": statuses["REPRODUCED"] - volume_only,
            "overlap_total": sum(result["overlap_count"] for result in results),
            "changed_overlap_total": sum(
                result["changed_overlap_count"] for result in results
            ),
            "new_candle_total": sum(result["new_candle_count"] for result in results),
            "omitted_trailing_total": sum(
                result["omitted_trailing_count"] for result in results
            ),
            "changed_fields": [
                {"field": field, "count": count}
                for field, count in sorted(fields.items())
            ],
            "provider_failure_categories": [
                {"category": category, "count": count}
                for category, count in sorted(failure_categories.items())
            ],
            "failure": None,
            "limitations": [
                "current responses cannot establish causes of earlier drift",
                "aggregate excludes series identities, prices, currencies, paths, candle timestamps, provider text, and exception messages",
                "diagnostic does not write candles or checkpoints",
            ],
        }

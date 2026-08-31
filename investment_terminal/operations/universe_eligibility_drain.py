"""Budgeted coordinator for complete resumable universe eligibility scans."""

from investment_terminal.operations.universe_eligibility_scan import (
    EligibilityScanRequest,
    UniverseEligibilityScanService,
)
from investment_terminal.utils.validation import validate_aware_datetime


class UniverseEligibilityDrainService:
    """Repeat unchanged bounded slices until a durable stopping condition."""

    def __init__(self, *, client, checkpoint_writer, clock) -> None:
        self.client = client
        self.checkpoint_writer = checkpoint_writer
        self.clock = clock

    def run(self, request: EligibilityScanRequest, checkpoint=None, *, max_total_items: int):
        if isinstance(max_total_items, bool) or not isinstance(max_total_items, int):
            raise TypeError("max_total_items must be an integer")
        if not 1 <= max_total_items <= 20000:
            raise ValueError("max_total_items must be between 1 and 20000")
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        current = checkpoint
        initial, _ = UniverseEligibilityScanService._outcomes(checkpoint, request)
        terminal_statuses = {"SUCCESS", "EMPTY", "FINAL_FAILED", "PROJECTION_FAILED"}
        initial_terminal = sum(item["status"] in terminal_statuses for item in initial.values())
        starting = {"terminal_count": initial_terminal,
            "pending_count": len(request.members) - initial_terminal}
        ending = None
        slices = attempted = provider_requests = 0

        def write(payload):
            nonlocal current
            self.checkpoint_writer(payload)
            current = payload

        service = UniverseEligibilityScanService(
            client=self.client, checkpoint_writer=write, clock=self.clock)
        while attempted < max_total_items:
            report = service.run(request, current,
                max_items=min(100, max_total_items - attempted))
            coverage = report["coverage"]
            run = coverage["current_run"]
            cumulative = coverage["cumulative"]
            ending = dict(cumulative)
            slices += 1
            attempted += run["attempted_count"]
            provider_requests += run["provider_request_count"]
            if report["status"] in {"COMPLETE", "PAUSED"}:
                break
            if run["attempted_count"] == 0:
                raise RuntimeError("Eligibility drain made zero progress")
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        status = report["status"] if report["status"] in {"COMPLETE", "PAUSED"} else "BUDGET_EXHAUSTED"
        return {
            "schema_version": 1,
            "operation_identity": "UNIVERSE_ELIGIBILITY_DRAIN",
            "provider_identity": "YAHOO_FINANCE",
            "status": status,
            "started_at": started.isoformat(), "completed_at": completed.isoformat(),
            "duration_seconds": (completed - started).total_seconds(),
            "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "requested_start": request.requested_start.isoformat(),
            "requested_end": request.requested_end.isoformat(),
            "budget": {"max_total_items": max_total_items, "slice_size": 100},
            "current_run": {"slice_count": slices, "attempted_count": attempted,
                "provider_request_count": provider_requests},
            "starting_coverage": starting,
            "ending_coverage": ending,
            "halt_category": report["halt_category"], "failure": None,
            "limitations": ["report excludes identities, values, paths, provider text, and exception messages",
                "eligibility completion does not authorize ranking or historical ingestion"],
        }

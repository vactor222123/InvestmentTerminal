"""Project a complete eligibility checkpoint into a private success universe."""

from datetime import datetime
from hashlib import sha256
import json

from investment_terminal.operations.universe_eligibility_scan import (
    EligibilityScanRequest,
    UniverseEligibilityScanService,
)
from investment_terminal.utils.validation import validate_aware_datetime


class EligibilitySuccessProjectionService:
    def __init__(self, *, clock) -> None:
        self.clock = clock

    def run(
        self,
        request: EligibilityScanRequest,
        checkpoint: object,
    ) -> tuple[dict[str, object], dict[str, object]]:
        started = validate_aware_datetime(self.clock(), field_name="started_at")
        outcomes, migrated = UniverseEligibilityScanService._outcomes(checkpoint, request)
        if migrated:
            raise ValueError("Eligibility projection requires schema-version-4 evidence")
        terminal = {"SUCCESS", "EMPTY", "FINAL_FAILED", "PROJECTION_FAILED"}
        if len(outcomes) != len(request.members) or any(
            item["status"] not in terminal for item in outcomes.values()
        ):
            raise ValueError("Eligibility checkpoint is not complete")
        members = [
            {
                "source": item.source,
                "source_symbol": item.source_symbol,
                "yahoo_symbol": item.yahoo_symbol,
            }
            for item in request.members
            if outcomes[item.key]["status"] == "SUCCESS"
        ]
        private = {
            "schema_version": 1,
            "projection_identity": "ELIGIBILITY_SUCCESS_UNIVERSE",
            "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "members": members,
        }
        projection_checksum = _checksum(private)
        completed = validate_aware_datetime(self.clock(), field_name="completed_at")
        report = {
            "schema_version": 1,
            "operation_identity": "ELIGIBILITY_SUCCESS_PROJECTION",
            "status": "SUCCESS",
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "duration_seconds": (completed-started).total_seconds(),
            "request_checksum": request.checksum,
            "universe_checksum": request.universe_checksum,
            "projection_checksum": projection_checksum,
            "coverage": {
                "member_count": len(request.members),
                "success_count": len(members),
                "excluded_count": len(request.members) - len(members),
            },
            "failure": None,
            "limitations": [
                "report excludes member identities, symbols, values, and paths",
                "projection does not authorize currency inference, ranking, batching, or ingestion",
            ],
        }
        return private, report


def _checksum(value: object) -> str:
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return sha256(serialized.encode("utf-8")).hexdigest()

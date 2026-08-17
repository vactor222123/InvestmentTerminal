"""Review Package projection for external-context evidence."""

from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
)


class ExternalContextReviewAdapter:
    """Project normalized context evidence into one JSON-ready section."""

    _STATUS_PRIORITY = {
        "READY": 0,
        "PARTIAL": 1,
        "STALE": 2,
    }

    @classmethod
    def adapt(
        cls,
        evidence: tuple[ExternalContextEvidence, ...],
    ) -> dict:
        if not isinstance(evidence, tuple):
            raise TypeError("evidence must be a tuple")
        if any(
            not isinstance(item, ExternalContextEvidence)
            for item in evidence
        ):
            raise TypeError(
                "evidence must contain only ExternalContextEvidence objects"
            )

        ordered = tuple(sorted(
            evidence,
            key=lambda item: (
                item.provenance.published_at,
                item.provenance.source,
                item.provenance.source_record_id,
                item.record.context_id,
            ),
        ))
        if not ordered:
            return {
                "status": "NO_EVIDENCE",
                "item_count": 0,
                "quality_counts": {
                    "READY": 0,
                    "PARTIAL": 0,
                    "STALE": 0,
                },
                "warnings": [],
                "items": [],
            }

        quality_counts = {
            status: sum(
                item.quality.status == status
                for item in ordered
            )
            for status in cls._STATUS_PRIORITY
        }
        status = max(
            (item.quality.status for item in ordered),
            key=cls._STATUS_PRIORITY.__getitem__,
        )
        warnings = tuple(dict.fromkeys(
            warning
            for item in ordered
            for warning in item.quality.warnings
        ))

        return {
            "status": status,
            "item_count": len(ordered),
            "quality_counts": quality_counts,
            "warnings": list(warnings),
            "items": [item.to_dict() for item in ordered],
        }

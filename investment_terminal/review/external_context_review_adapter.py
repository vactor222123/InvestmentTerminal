"""Review Package projection for external-context evidence."""

from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
)
from investment_terminal.context.external_context_sentiment import (
    EXTERNAL_CONTEXT_SENTIMENT_LABELS,
    ExternalContextSentimentEvidence,
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
        *,
        sentiment: tuple[ExternalContextSentimentEvidence, ...] = (),
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
        if not isinstance(sentiment, tuple):
            raise TypeError("sentiment must be a tuple")
        if any(
            not isinstance(item, ExternalContextSentimentEvidence)
            for item in sentiment
        ):
            raise TypeError(
                "sentiment must contain only "
                "ExternalContextSentimentEvidence objects"
            )

        sentiment_by_context_id = {
            item.context_id: item
            for item in sentiment
        }
        if len(sentiment_by_context_id) != len(sentiment):
            raise ValueError(
                "sentiment must contain unique context_id values"
            )
        evidence_context_ids = {
            item.record.context_id
            for item in evidence
        }
        orphaned = tuple(sorted(
            set(sentiment_by_context_id) - evidence_context_ids
        ))
        if orphaned:
            raise ValueError(
                "sentiment references unknown context_id values: "
                + ", ".join(orphaned)
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
                "sentiment_counts": {
                    **{
                        label: 0
                        for label in EXTERNAL_CONTEXT_SENTIMENT_LABELS
                    },
                    "NOT_ASSESSED": 0,
                },
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
        sentiment_counts = {
            label: sum(
                assessment.label == label
                for assessment in sentiment
            )
            for label in EXTERNAL_CONTEXT_SENTIMENT_LABELS
        }
        sentiment_counts["NOT_ASSESSED"] = (
            len(ordered) - len(sentiment)
        )

        items = []
        for item in ordered:
            payload = item.to_dict()
            assessment = sentiment_by_context_id.get(
                item.record.context_id
            )
            payload["sentiment"] = (
                assessment.to_dict()
                if assessment is not None
                else {"status": "NOT_ASSESSED"}
            )
            items.append(payload)

        return {
            "status": status,
            "item_count": len(ordered),
            "quality_counts": quality_counts,
            "warnings": list(warnings),
            "sentiment_counts": sentiment_counts,
            "items": items,
        }

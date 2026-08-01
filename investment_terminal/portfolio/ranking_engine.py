"""
Deterministic portfolio ranking engine.
"""

from collections.abc import Iterable
from datetime import datetime, timezone

from investment_terminal.decision_engine.decision_model import (
    DecisionResult,
)
from investment_terminal.portfolio.ranking_models import (
    RankingCandidate,
    RankingResult,
)


class RankingEngine:
    """
    Rank analyzed assets using deterministic comparison rules.
    """

    SCHEMA_VERSION = "1.0"

    def rank(
        self,
        decisions: list[DecisionResult]
        | tuple[DecisionResult, ...],
        generated_at: datetime | None = None,
    ) -> RankingResult:
        """
        Sort decisions and assign consecutive ranks.
        """
        normalized_decisions = self._validate_decisions(
            decisions
        )

        if generated_at is None:
            ranking_generated_at = datetime.now(
                timezone.utc
            )
        else:
            if not isinstance(
                generated_at,
                datetime,
            ):
                raise TypeError(
                    "generated_at must be a datetime"
                )

            ranking_generated_at = generated_at

        ordered = sorted(
            normalized_decisions,
            key=self._sort_key,
        )

        candidates = tuple(
            RankingCandidate(
                rank=index,
                decision=decision,
            )
            for index, decision in enumerate(
                ordered,
                start=1,
            )
        )

        return RankingResult(
            schema_version=self.SCHEMA_VERSION,
            generated_at=ranking_generated_at,
            candidates=candidates,
        )

    @staticmethod
    def _sort_key(
        decision: DecisionResult,
    ) -> tuple[
        float,
        float,
        float,
        float,
        str,
    ]:
        """
        Return a stable ascending sort key.

        Numeric values are negated so larger scores rank first.
        """
        return (
            -decision.scores.overall,
            -decision.confidence.score,
            -decision.scores.fundamental,
            -decision.scores.technical,
            decision.symbol,
        )

    @staticmethod
    def _validate_decisions(
        decisions: object,
    ) -> tuple[DecisionResult, ...]:
        """
        Validate and normalize the decision collection.
        """
        if not isinstance(
            decisions,
            (list, tuple),
        ):
            raise TypeError(
                "decisions must be a list or tuple"
            )

        if not decisions:
            raise ValueError(
                "decisions must not be empty"
            )

        if any(
            not isinstance(
                decision,
                DecisionResult,
            )
            for decision in decisions
        ):
            raise TypeError(
                "decisions must contain only "
                "DecisionResult objects"
            )

        symbols = [
            decision.symbol
            for decision in decisions
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "decisions must contain unique symbols"
            )

        return tuple(decisions)
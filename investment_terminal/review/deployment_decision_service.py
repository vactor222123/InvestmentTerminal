"""
Build a machine deployment decision from review-package evidence.
"""

from collections import Counter

from investment_terminal.review.deployment_decision_models import (
    DeploymentDecision,
)


class DeploymentDecisionService:
    """
    Convert recommendation breadth and data readiness into a cautious
    deployment mode.

    External context is not yet integrated, so the service caps machine
    deployment at 50 percent even when the internal signal is strong.
    """

    POSITIVE = {
        "BUY",
        "ACCUMULATE",
    }
    NEUTRAL = {
        "HOLD",
        "WATCH",
    }
    NEGATIVE = {
        "AVOID",
        "SELL",
    }

    def decide(
        self,
        *,
        data_freshness: dict,
        machine_recommendations: dict,
    ) -> DeploymentDecision:
        if not isinstance(data_freshness, dict):
            raise TypeError(
                "data_freshness must be a dict"
            )

        if not isinstance(
            machine_recommendations,
            dict,
        ):
            raise TypeError(
                "machine_recommendations must be a dict"
            )

        freshness_source = data_freshness.get(
            "source",
            {}
        )
        all_ready = bool(
            freshness_source.get(
                "all_ready",
                False,
            )
        )

        recommendations = (
            machine_recommendations
            .get(
                "recommendations",
                {}
            )
            .get(
                "items",
                []
            )
        )

        if not isinstance(
            recommendations,
            list,
        ):
            raise TypeError(
                "recommendation items must be a list"
            )

        labels = tuple(
            str(
                item.get(
                    "recommendation",
                    "",
                )
            )
            .strip()
            .upper()
            for item in recommendations
        )
        counts = Counter(labels)

        positive_count = sum(
            counts[label]
            for label in self.POSITIVE
        )
        neutral_count = sum(
            counts[label]
            for label in self.NEUTRAL
        )
        negative_count = sum(
            counts[label]
            for label in self.NEGATIVE
        )
        universe_size = len(labels)

        unclassified = (
            universe_size
            - positive_count
            - neutral_count
            - negative_count
        )
        neutral_count += unclassified

        if (
            not all_ready
            or universe_size == 0
        ):
            return DeploymentDecision(
                mode="WAIT",
                deployment_fraction=0.0,
                confidence="LOW",
                positive_count=positive_count,
                neutral_count=neutral_count,
                negative_count=negative_count,
                universe_size=universe_size,
                reasons=(
                    "Verified recommendation evidence is not fully ready.",
                ),
                cautions=(
                    "Do not deploy capital from incomplete market data.",
                    "External context is not connected.",
                ),
            )

        positive_breadth = (
            positive_count
            / universe_size
        )
        negative_breadth = (
            negative_count
            / universe_size
        )

        if (
            positive_breadth >= 0.50
            and negative_breadth <= 0.10
        ):
            mode = "PARTIAL_DEPLOYMENT"
            fraction = 0.50
            confidence = "HIGH"
            reason = (
                "At least half of the analyzed universe has a "
                "positive machine recommendation."
            )
        elif (
            positive_breadth >= 0.25
            and negative_breadth <= 0.20
        ):
            mode = "PARTIAL_DEPLOYMENT"
            fraction = 0.25
            confidence = "MEDIUM"
            reason = (
                "A meaningful minority of the analyzed universe has "
                "a positive machine recommendation."
            )
        else:
            mode = "WAIT"
            fraction = 0.0
            confidence = "MEDIUM"
            reason = (
                "Positive recommendation breadth is not strong enough "
                "for deployment."
            )

        return DeploymentDecision(
            mode=mode,
            deployment_fraction=fraction,
            confidence=confidence,
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            universe_size=universe_size,
            reasons=(
                reason,
                "All analyzed market-data records are ready.",
            ),
            cautions=(
                "ETF analysis is not connected.",
                "Current portfolio market prices are not connected.",
                "News, macroeconomic, and geopolitical context "
                "must be reviewed externally.",
            ),
        )
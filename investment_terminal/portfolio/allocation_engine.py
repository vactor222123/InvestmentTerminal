"""
Score-based portfolio allocation engine.
"""

from datetime import datetime, timezone
from math import isfinite
from numbers import Real

from investment_terminal.portfolio.allocation_models import (
    AllocationConstraints,
    PortfolioAllocationPosition,
    PortfolioAllocationResult,
)
from investment_terminal.portfolio.recommendation_models import (
    CandidateRecommendation,
    PortfolioRecommendationResult,
)


PROFILE_CONSTRAINTS = {
    "CONSERVATIVE": AllocationConstraints(
        profile="CONSERVATIVE",
        minimum_position_weight=0.05,
        maximum_position_weight=0.25,
        cash_reserve_weight=0.20,
    ),
    "BALANCED": AllocationConstraints(
        profile="BALANCED",
        minimum_position_weight=0.05,
        maximum_position_weight=0.30,
        cash_reserve_weight=0.10,
    ),
    "GROWTH": AllocationConstraints(
        profile="GROWTH",
        minimum_position_weight=0.05,
        maximum_position_weight=0.35,
        cash_reserve_weight=0.05,
    ),
}

RECOMMENDATION_MULTIPLIERS = {
    "STRONG_BUY": 1.20,
    "BUY": 1.10,
    "ACCUMULATE": 1.00,
    "HOLD": 0.65,
    "WATCH": 0.00,
    "AVOID": 0.00,
}

RISK_MULTIPLIERS = {
    "LOW": 1.00,
    "MEDIUM": 0.85,
    "HIGH": 0.65,
    "VERY HIGH": 0.45,
}


class PortfolioAllocationEngine:
    """
    Build constrained target weights from recommendation results.

    The allocation score combines:

    - overall analytical score;
    - recommendation strength;
    - confidence;
    - current risk level.

    WATCH and AVOID candidates remain visible with zero weight.
    """

    SCHEMA_VERSION = "1.0"

    def allocate(
        self,
        recommendations: PortfolioRecommendationResult,
        *,
        total_capital: float,
        profile: str = "BALANCED",
        currency: str = "USD",
        generated_at: datetime | None = None,
        constraints: AllocationConstraints | None = None,
        max_positions: int | None = None,
    ) -> PortfolioAllocationResult:
        """
        Generate a target allocation for a recommendation universe.
        """
        if not isinstance(
            recommendations,
            PortfolioRecommendationResult,
        ):
            raise TypeError(
                "recommendations must be a "
                "PortfolioRecommendationResult"
            )

        resolved_capital = self._validate_positive_number(
            total_capital,
            field_name="total_capital",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )
        resolved_generated_at = self._resolve_generated_at(
            generated_at
        )
        resolved_constraints = self._resolve_constraints(
            profile=profile,
            constraints=constraints,
        )
        resolved_max_positions = self._validate_max_positions(
            max_positions
        )

        if any(
            recommendation.currency
            != normalized_currency
            for recommendation
            in recommendations.recommendations
        ):
            raise ValueError(
                "recommendation currencies must match "
                "the allocation currency"
            )

        scores = tuple(
            self._allocation_score(
                recommendation
            )
            for recommendation
            in recommendations.recommendations
        )

        eligible_indices = tuple(
            index
            for index, score in enumerate(scores)
            if score > 0
        )

        if resolved_max_positions is not None:
            eligible_indices = eligible_indices[
                :resolved_max_positions
            ]

        if not eligible_indices:
            raise ValueError(
                "at least one recommendation must be "
                "eligible for allocation"
            )

        self._validate_constraint_feasibility(
            eligible_count=len(eligible_indices),
            constraints=resolved_constraints,
        )

        eligible_scores = tuple(
            scores[index]
            for index in eligible_indices
        )

        eligible_weights = self._bounded_weights(
            scores=eligible_scores,
            total_weight=(
                resolved_constraints
                .investable_weight
            ),
            minimum_weight=(
                resolved_constraints
                .minimum_position_weight
            ),
            maximum_weight=(
                resolved_constraints
                .maximum_position_weight
            ),
        )

        weights_by_index = {
            index: weight
            for index, weight in zip(
                eligible_indices,
                eligible_weights,
                strict=True,
            )
        }

        ordered_weights = tuple(
            weights_by_index.get(
                index,
                0.0,
            )
            for index in range(
                len(
                    recommendations.recommendations
                )
            )
        )

        target_amounts = self._allocate_amounts(
            total_capital=resolved_capital,
            weights=ordered_weights,
            cash_reserve_weight=(
                resolved_constraints
                .cash_reserve_weight
            ),
        )

        positions = tuple(
            self._build_position(
                recommendation=recommendation,
                target_weight=ordered_weights[index],
                target_amount=target_amounts[index],
                allocation_score=scores[index],
            )
            for index, recommendation in enumerate(
                recommendations.recommendations
            )
        )

        return PortfolioAllocationResult(
            schema_version=self.SCHEMA_VERSION,
            generated_at=resolved_generated_at,
            total_capital=resolved_capital,
            currency=normalized_currency,
            constraints=resolved_constraints,
            positions=positions,
            cash_amount=round(
                resolved_capital
                * resolved_constraints
                .cash_reserve_weight,
                2,
            ),
        )

    @staticmethod
    def default_constraints(
        profile: str,
    ) -> AllocationConstraints:
        """
        Return predefined constraints for one risk profile.
        """
        normalized_profile = (
            AllocationConstraints
            ._normalize_profile(
                profile
            )
        )

        return PROFILE_CONSTRAINTS[
            normalized_profile
        ]

    @classmethod
    def _allocation_score(
        cls,
        recommendation: CandidateRecommendation,
    ) -> float:
        recommendation_multiplier = (
            RECOMMENDATION_MULTIPLIERS[
                recommendation.recommendation
            ]
        )

        if recommendation_multiplier == 0:
            return 0.0

        risk_multiplier = RISK_MULTIPLIERS.get(
            recommendation.risk_level,
            0.50,
        )
        confidence_factor = (
            recommendation.confidence_score
            / 100.0
        )

        score = (
            recommendation.overall_score
            * recommendation_multiplier
            * risk_multiplier
            * confidence_factor
        )

        return round(
            max(score, 0.0),
            8,
        )

    @classmethod
    def _bounded_weights(
        cls,
        *,
        scores: tuple[float, ...],
        total_weight: float,
        minimum_weight: float,
        maximum_weight: float,
    ) -> tuple[float, ...]:
        """
        Normalize scores while respecting lower and upper bounds.
        """
        count = len(scores)

        if count == 0:
            raise ValueError(
                "scores must not be empty"
            )

        if any(
            score <= 0
            for score in scores
        ):
            raise ValueError(
                "scores must be greater than zero"
            )

        weights = [
            minimum_weight
            for _ in scores
        ]
        remaining = (
            total_weight
            - minimum_weight * count
        )

        active = set(
            range(count)
        )

        while (
            remaining > 1e-12
            and active
        ):
            active_score = sum(
                scores[index]
                for index in active
            )

            if active_score <= 0:
                equal_share = (
                    remaining
                    / len(active)
                )
                proposals = {
                    index: equal_share
                    for index in active
                }
            else:
                proposals = {
                    index: (
                        remaining
                        * scores[index]
                        / active_score
                    )
                    for index in active
                }

            capped = []

            for index in active:
                capacity = (
                    maximum_weight
                    - weights[index]
                )

                if (
                    proposals[index]
                    >= capacity - 1e-12
                ):
                    weights[index] += capacity
                    remaining -= capacity
                    capped.append(index)

            if capped:
                active.difference_update(
                    capped
                )
                continue

            for index in active:
                weights[index] += (
                    proposals[index]
                )

            remaining = 0.0

        if remaining > 1e-9:
            raise ValueError(
                "allocation constraints cannot absorb "
                "the investable weight"
            )

        rounded = [
            round(weight, 10)
            for weight in weights
        ]
        difference = round(
            total_weight - sum(rounded),
            10,
        )

        if abs(difference) > 0:
            adjustable = max(
                range(count),
                key=lambda index: (
                    maximum_weight
                    - rounded[index]
                ),
            )
            rounded[adjustable] = round(
                rounded[adjustable]
                + difference,
                10,
            )

        return tuple(rounded)

    @classmethod
    def _build_position(
        cls,
        *,
        recommendation: CandidateRecommendation,
        target_weight: float,
        target_amount: float,
        allocation_score: float,
    ) -> PortfolioAllocationPosition:
        return PortfolioAllocationPosition(
            recommendation=recommendation,
            target_weight=target_weight,
            target_amount=target_amount,
            allocation_score=allocation_score,
            explanation=cls._build_explanation(
                recommendation=recommendation,
                target_weight=target_weight,
            ),
        )

    @staticmethod
    def _allocate_amounts(
        *,
        total_capital: float,
        weights: tuple[float, ...],
        cash_reserve_weight: float,
    ) -> tuple[float, ...]:
        """
        Convert target weights to exact currency-cent amounts.

        The largest-remainder method prevents independent rounding
        from creating a portfolio total that differs by a few cents.
        """
        total_cents = round(
            total_capital * 100
        )
        cash_cents = round(
            total_capital
            * cash_reserve_weight
            * 100
        )
        investable_cents = (
            total_cents - cash_cents
        )

        exact_cents = [
            total_capital
            * weight
            * 100
            for weight in weights
        ]
        allocated_cents = [
            int(value)
            for value in exact_cents
        ]

        remaining_cents = (
            investable_cents
            - sum(allocated_cents)
        )

        if remaining_cents < 0:
            raise RuntimeError(
                "rounded position amounts exceed "
                "the investable capital"
            )

        remainder_order = sorted(
            range(len(weights)),
            key=lambda index: (
                exact_cents[index]
                - allocated_cents[index],
                weights[index],
                -index,
            ),
            reverse=True,
        )

        for index in remainder_order[
            :remaining_cents
        ]:
            allocated_cents[index] += 1

        if sum(allocated_cents) != investable_cents:
            raise RuntimeError(
                "position amount allocation did not "
                "consume investable capital"
            )

        return tuple(
            cents / 100.0
            for cents in allocated_cents
        )

    @staticmethod
    def _build_explanation(
        *,
        recommendation: CandidateRecommendation,
        target_weight: float,
    ) -> str:
        if target_weight == 0:
            if recommendation.recommendation in {
                "WATCH",
                "AVOID",
            }:
                return (
                    f"{recommendation.symbol} receives no target "
                    f"allocation because its analytical label is "
                    f"{recommendation.recommendation}."
                )

            return (
                f"{recommendation.symbol} remains in the market "
                "ranking but receives no target allocation because "
                "it is outside the selected funded-position limit."
            )

        return (
            f"{recommendation.symbol} receives a "
            f"{target_weight * 100.0:.2f}% target weight. "
            f"The allocation reflects an overall score of "
            f"{recommendation.overall_score:.2f}, a "
            f"{recommendation.recommendation} recommendation, "
            f"{recommendation.confidence_score:.2f}% confidence, "
            f"and a {recommendation.risk_level} risk level."
        )

    @staticmethod
    def _validate_max_positions(
        value: int | None,
    ) -> int | None:
        """
        Validate the optional maximum number of funded positions.
        """
        if value is None:
            return None

        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                "max_positions must be an integer or None"
            )

        if value <= 0:
            raise ValueError(
                "max_positions must be greater than zero"
            )

        return value

    @staticmethod
    def _validate_constraint_feasibility(
        *,
        eligible_count: int,
        constraints: AllocationConstraints,
    ) -> None:
        investable = (
            constraints.investable_weight
        )
        minimum_total = (
            eligible_count
            * constraints
            .minimum_position_weight
        )
        maximum_total = (
            eligible_count
            * constraints
            .maximum_position_weight
        )

        if minimum_total > investable + 1e-9:
            raise ValueError(
                "minimum_position_weight is too high "
                "for the eligible universe"
            )

        if maximum_total + 1e-9 < investable:
            raise ValueError(
                "maximum_position_weight is too low "
                "for the eligible universe"
            )

    @classmethod
    def _resolve_constraints(
        cls,
        *,
        profile: str,
        constraints: AllocationConstraints | None,
    ) -> AllocationConstraints:
        if constraints is not None:
            if not isinstance(
                constraints,
                AllocationConstraints,
            ):
                raise TypeError(
                    "constraints must be an "
                    "AllocationConstraints or None"
                )

            normalized_profile = (
                AllocationConstraints
                ._normalize_profile(
                    profile
                )
            )

            if (
                constraints.profile
                != normalized_profile
            ):
                raise ValueError(
                    "profile must match "
                    "constraints.profile"
                )

            return constraints

        return cls.default_constraints(
            profile
        )

    @staticmethod
    def _resolve_generated_at(
        generated_at: datetime | None,
    ) -> datetime:
        if generated_at is None:
            return datetime.now(
                timezone.utc
            )

        if not isinstance(
            generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        if (
            generated_at.tzinfo is None
            or generated_at.utcoffset() is None
        ):
            raise ValueError(
                "generated_at must be timezone-aware"
            )

        return generated_at.astimezone(
            timezone.utc
        )

    @staticmethod
    def _normalize_text(
        value: object,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be "
                "a non-empty string"
            )

        return value.strip().upper()

    @staticmethod
    def _validate_positive_number(
        value: object,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
        ):
            raise ValueError(
                f"{field_name} must be "
                "a finite number"
            )

        numeric = float(value)

        if numeric <= 0:
            raise ValueError(
                f"{field_name} must be "
                "greater than zero"
            )

        return numeric
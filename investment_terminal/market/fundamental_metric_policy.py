"""
Business-model-aware fundamental metric applicability policy.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)


LIQUIDITY_METRICS = frozenset(
    {
        "current_ratio",
        "quick_ratio",
    }
)

CAPITAL_STRUCTURE_METRICS = frozenset(
    {
        "debt_to_equity",
    }
)

STANDARD_METRICS = frozenset(
    {
        "revenue_growth",
        "earnings_growth",
        "gross_margin",
        "operating_margin",
        "net_margin",
        "return_on_equity",
        "return_on_invested_capital",
        "debt_to_equity",
        "current_ratio",
        "quick_ratio",
        "operating_cash_flow",
        "free_cash_flow",
        "forward_pe",
        "price_to_sales",
        "peg_ratio",
        "enterprise_to_ebitda",
        "dividend_yield",
        "payout_ratio",
    }
)


@dataclass(frozen=True, slots=True)
class MetricApplicability:
    """Decision describing whether one metric should affect scoring."""

    metric_name: str
    applicable: bool
    reason: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.metric_name, str)
            or not self.metric_name.strip()
        ):
            raise ValueError(
                "metric_name must be a non-empty string"
            )

        if not isinstance(self.applicable, bool):
            raise TypeError(
                "applicable must be a bool"
            )

        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )

        object.__setattr__(
            self,
            "metric_name",
            self.metric_name.strip(),
        )
        object.__setattr__(
            self,
            "reason",
            self.reason.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "applicable": self.applicable,
            "reason": self.reason,
        }


class FundamentalMetricPolicy:
    """
    Decide which generic metrics are meaningful for a business model.

    This policy suppresses only metrics known to be structurally
    misleading. It does not invent replacement metrics.
    """

    def evaluate(
        self,
        classification: CompanyClassification,
        metric_name: str,
    ) -> MetricApplicability:
        if not isinstance(
            classification,
            CompanyClassification,
        ):
            raise TypeError(
                "classification must be a CompanyClassification"
            )

        normalized_metric = self._normalize_metric_name(
            metric_name
        )

        if normalized_metric not in STANDARD_METRICS:
            return MetricApplicability(
                metric_name=normalized_metric,
                applicable=False,
                reason=(
                    "The metric is not registered in the "
                    "fundamental applicability policy."
                ),
            )

        business_model = classification.business_model

        if (
            business_model
            in {
                "BANK",
                "PAYMENT_NETWORK",
                "INSURER",
            }
            and normalized_metric in LIQUIDITY_METRICS
        ):
            return MetricApplicability(
                metric_name=normalized_metric,
                applicable=False,
                reason=(
                    f"{normalized_metric} is excluded for "
                    f"{business_model} because generic corporate "
                    "liquidity thresholds are not directly "
                    "comparable for this business model."
                ),
            )

        if (
            business_model == "BANK"
            and normalized_metric in CAPITAL_STRUCTURE_METRICS
        ):
            return MetricApplicability(
                metric_name=normalized_metric,
                applicable=False,
                reason=(
                    "debt_to_equity is excluded for BANK because "
                    "deposits and financial leverage are structural "
                    "parts of the business model."
                ),
            )

        return MetricApplicability(
            metric_name=normalized_metric,
            applicable=True,
            reason=(
                f"{normalized_metric} is applicable to "
                f"{business_model} under the current policy."
            ),
        )

    def is_applicable(
        self,
        classification: CompanyClassification,
        metric_name: str,
    ) -> bool:
        return self.evaluate(
            classification,
            metric_name,
        ).applicable

    def applicable_metrics(
        self,
        classification: CompanyClassification,
    ) -> tuple[str, ...]:
        return tuple(
            metric
            for metric in sorted(STANDARD_METRICS)
            if self.is_applicable(
                classification,
                metric,
            )
        )

    def excluded_metrics(
        self,
        classification: CompanyClassification,
    ) -> tuple[MetricApplicability, ...]:
        return tuple(
            result
            for result in (
                self.evaluate(
                    classification,
                    metric,
                )
                for metric in sorted(STANDARD_METRICS)
            )
            if not result.applicable
        )

    @staticmethod
    def _normalize_metric_name(
        value: object,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                "metric_name must be a non-empty string"
            )

        return (
            value.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
"""
Business-model-aware fundamental scoring service.
"""

from investment_terminal.clients.fundamental_data_client import (
    FundamentalDataClient,
)
from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)
from investment_terminal.market.company_classification_registry import (
    CompanyClassificationRegistry,
)
from investment_terminal.market.fundamental_metric_policy import (
    FundamentalMetricPolicy,
)
from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreBreakdown,
    FundamentalScoreResult,
    FundamentalScoreService,
)


class SectorAwareFundamentalScoreService:
    """
    Score fundamentals after removing structurally inapplicable metrics.

    Generic scoring remains the default for unclassified symbols. This
    keeps the pipeline usable while the classification registry expands.
    """

    def __init__(
        self,
        client: FundamentalDataClient,
        registry: CompanyClassificationRegistry,
        policy: FundamentalMetricPolicy | None = None,
    ) -> None:
        if not isinstance(
            registry,
            CompanyClassificationRegistry,
        ):
            raise TypeError(
                "registry must be a CompanyClassificationRegistry"
            )

        self.client = client
        self.registry = registry
        self.policy = (
            policy
            if policy is not None
            else FundamentalMetricPolicy()
        )
        self.generic_service = FundamentalScoreService(
            client
        )

    def score(
        self,
        symbol: str,
        currency: str = "USD",
    ) -> FundamentalScoreResult:
        snapshot = self.client.get_fundamentals(
            symbol=symbol,
            currency=currency,
        )
        return self.score_snapshot(snapshot)

    def score_snapshot(
        self,
        snapshot: FundamentalSnapshot,
    ) -> FundamentalScoreResult:
        if not isinstance(
            snapshot,
            FundamentalSnapshot,
        ):
            raise TypeError(
                "snapshot must be a FundamentalSnapshot"
            )

        classification = self.registry.get(
            snapshot.symbol
        )

        if classification is None:
            return self.generic_service.score_snapshot(
                snapshot
            )

        return self._score_classified_snapshot(
            snapshot,
            classification,
        )

    def _score_classified_snapshot(
        self,
        snapshot: FundamentalSnapshot,
        classification: CompanyClassification,
    ) -> FundamentalScoreResult:
        positive_factors: list[str] = []
        risk_factors: list[str] = []

        growth = FundamentalScoreService._score_growth(
            snapshot,
            positive_factors,
            risk_factors,
        )
        profitability = (
            FundamentalScoreService._score_profitability(
                snapshot,
                positive_factors,
                risk_factors,
            )
        )
        balance_sheet = self._score_balance_sheet(
            snapshot,
            classification,
            positive_factors,
            risk_factors,
        )
        cash_flow = FundamentalScoreService._score_cash_flow(
            snapshot,
            positive_factors,
            risk_factors,
        )
        valuation = FundamentalScoreService._score_valuation(
            snapshot,
            positive_factors,
            risk_factors,
        )
        shareholder_returns = (
            FundamentalScoreService._score_shareholder_returns(
                snapshot,
                positive_factors,
                risk_factors,
            )
        )

        breakdown = FundamentalScoreBreakdown(
            growth=growth,
            profitability=profitability,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            valuation=valuation,
            shareholder_returns=shareholder_returns,
        )
        raw_score = (
            growth
            + profitability
            + balance_sheet
            + cash_flow
            + valuation
            + shareholder_returns
        )

        applicable_fields = self.policy.applicable_metrics(
            classification
        )
        missing_fields = tuple(
            field_name
            for field_name in applicable_fields
            if getattr(
                snapshot,
                field_name,
                None,
            ) is None
        )
        available_count = (
            len(applicable_fields)
            - len(missing_fields)
        )
        data_quality_factor = (
            available_count / len(applicable_fields)
            if applicable_fields
            else 0.0
        )

        if missing_fields:
            risk_factors.append(
                "Some applicable fundamental metrics are unavailable."
            )

        final_score = raw_score * data_quality_factor

        return FundamentalScoreResult(
            symbol=snapshot.symbol,
            currency=snapshot.currency,
            raw_score=round(raw_score, 2),
            data_quality_factor=round(
                data_quality_factor,
                4,
            ),
            final_score=round(final_score, 2),
            classification=(
                FundamentalScoreService._classify_score(
                    final_score
                )
            ),
            breakdown=breakdown,
            positive_factors=tuple(positive_factors),
            risk_factors=tuple(risk_factors),
            missing_fields=missing_fields,
        )

    def _score_balance_sheet(
        self,
        snapshot: FundamentalSnapshot,
        classification: CompanyClassification,
        positive: list[str],
        risks: list[str],
    ) -> float:
        metrics: list[tuple[float, float]] = []

        if self.policy.is_applicable(
            classification,
            "debt_to_equity",
        ) and snapshot.debt_to_equity is not None:
            value = snapshot.debt_to_equity

            if value <= 0.5:
                points = 7.0
                positive.append(
                    "Debt-to-equity is conservative."
                )
            elif value <= 1.0:
                points = 5.0
            elif value <= 2.0:
                points = 2.5
                risks.append(
                    "Debt-to-equity is elevated."
                )
            else:
                points = 0.0
                risks.append(
                    "Debt-to-equity is high."
                )

            metrics.append((points, 7.0))

        if self.policy.is_applicable(
            classification,
            "current_ratio",
        ) and snapshot.current_ratio is not None:
            value = snapshot.current_ratio

            if 1.2 <= value <= 3.0:
                points = 4.0
                positive.append(
                    "Current liquidity is healthy."
                )
            elif value >= 1.0:
                points = 2.5
            else:
                points = 0.0
                risks.append(
                    "Current ratio is below one."
                )

            metrics.append((points, 4.0))

        if self.policy.is_applicable(
            classification,
            "quick_ratio",
        ) and snapshot.quick_ratio is not None:
            value = snapshot.quick_ratio

            if value >= 1.0:
                points = 4.0
            elif value >= 0.7:
                points = 2.0
            else:
                points = 0.0
                risks.append(
                    "Quick liquidity is weak."
                )

            metrics.append((points, 4.0))

        return FundamentalScoreService._normalize_component(
            metrics,
            component_max=15.0,
        )
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

    Component maxima are dynamic. A component with no applicable generic
    metrics receives a maximum of zero and does not reduce the normalized
    overall score. No positive score is invented for excluded metrics.
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
        profitability = FundamentalScoreService._score_profitability(
            snapshot,
            positive_factors,
            risk_factors,
        )
        balance_sheet, balance_sheet_max = self._score_balance_sheet(
            snapshot,
            classification,
            positive_factors,
            risk_factors,
        )
        cash_flow, cash_flow_max = self._score_cash_flow(
            snapshot,
            classification,
            positive_factors,
            risk_factors,
        )
        valuation, valuation_max = self._score_valuation(
            snapshot,
            classification,
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
            growth_max=20.0,
            profitability_max=25.0,
            balance_sheet_max=balance_sheet_max,
            cash_flow_max=cash_flow_max,
            valuation_max=valuation_max,
            shareholder_returns_max=5.0,
        )

        earned_score = (
            growth
            + profitability
            + balance_sheet
            + cash_flow
            + valuation
            + shareholder_returns
        )
        applicable_maximum = (
            breakdown.growth_max
            + breakdown.profitability_max
            + breakdown.balance_sheet_max
            + breakdown.cash_flow_max
            + breakdown.valuation_max
            + breakdown.shareholder_returns_max
        )
        raw_score = (
            earned_score
            / applicable_maximum
            * 100.0
            if applicable_maximum > 0
            else 0.0
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

        if classification.business_model == "BANK":
            risk_factors.append(
                "Specialized bank metrics are not yet available; "
                "the score uses a reduced generic metric set."
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
    ) -> tuple[float, float]:
        metrics: list[tuple[float, float]] = []

        if self.policy.is_applicable(
            classification,
            "debt_to_equity",
        ):
            maximum = 7.0
            if snapshot.debt_to_equity is not None:
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

                metrics.append((points, maximum))
            else:
                metrics.append((0.0, maximum))

        if self.policy.is_applicable(
            classification,
            "current_ratio",
        ):
            maximum = 4.0
            if snapshot.current_ratio is not None:
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

                metrics.append((points, maximum))
            else:
                metrics.append((0.0, maximum))

        if self.policy.is_applicable(
            classification,
            "quick_ratio",
        ):
            maximum = 4.0
            if snapshot.quick_ratio is not None:
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

                metrics.append((points, maximum))
            else:
                metrics.append((0.0, maximum))

        maximum = sum(item[1] for item in metrics)
        score = FundamentalScoreService._normalize_component(
            metrics,
            component_max=maximum,
        ) if maximum > 0 else 0.0

        return score, maximum

    def _score_cash_flow(
        self,
        snapshot: FundamentalSnapshot,
        classification: CompanyClassification,
        positive: list[str],
        risks: list[str],
    ) -> tuple[float, float]:
        metrics: list[tuple[float, float]] = []

        definitions = (
            (
                "operating_cash_flow",
                snapshot.operating_cash_flow,
                7.0,
                "Operating cash flow is positive.",
                "Operating cash flow is negative.",
            ),
            (
                "free_cash_flow",
                snapshot.free_cash_flow,
                8.0,
                "Free cash flow is positive.",
                "Free cash flow is negative.",
            ),
        )

        for (
            metric_name,
            value,
            maximum,
            positive_message,
            risk_message,
        ) in definitions:
            if not self.policy.is_applicable(
                classification,
                metric_name,
            ):
                continue

            if value is None:
                metrics.append((0.0, maximum))
                continue

            points = maximum if value > 0 else 0.0
            metrics.append((points, maximum))

            if value > 0:
                positive.append(positive_message)
            else:
                risks.append(risk_message)

        maximum = sum(item[1] for item in metrics)
        score = FundamentalScoreService._normalize_component(
            metrics,
            component_max=maximum,
        ) if maximum > 0 else 0.0

        return score, maximum

    def _score_valuation(
        self,
        snapshot: FundamentalSnapshot,
        classification: CompanyClassification,
        positive: list[str],
        risks: list[str],
    ) -> tuple[float, float]:
        metrics: list[tuple[float, float]] = []

        definitions = (
            (
                "forward_pe",
                snapshot.forward_pe,
                6.0,
                (15.0, 25.0, 40.0),
                "Forward P/E is attractive.",
                "Forward P/E is elevated.",
            ),
            (
                "peg_ratio",
                snapshot.peg_ratio,
                5.0,
                (1.0, 2.0, 3.0),
                "PEG ratio is attractive.",
                "PEG ratio is elevated.",
            ),
            (
                "enterprise_to_ebitda",
                snapshot.enterprise_to_ebitda,
                5.0,
                (10.0, 18.0, 30.0),
                "EV/EBITDA is attractive.",
                "EV/EBITDA is elevated.",
            ),
            (
                "price_to_sales",
                snapshot.price_to_sales,
                4.0,
                (3.0, 8.0, 15.0),
                "Price-to-sales is moderate.",
                "Price-to-sales is elevated.",
            ),
        )

        for (
            metric_name,
            value,
            maximum,
            thresholds,
            positive_message,
            risk_message,
        ) in definitions:
            if not self.policy.is_applicable(
                classification,
                metric_name,
            ):
                continue

            if value is None:
                metrics.append((0.0, maximum))
                continue

            points = FundamentalScoreService._inverse_threshold_points(
                value=value,
                maximum=maximum,
                attractive=thresholds[0],
                acceptable=thresholds[1],
                expensive=thresholds[2],
            )
            metrics.append((points, maximum))

            if value <= thresholds[0]:
                positive.append(positive_message)
            elif value > thresholds[2]:
                risks.append(risk_message)

        maximum = sum(item[1] for item in metrics)
        score = FundamentalScoreService._normalize_component(
            metrics,
            component_max=maximum,
        ) if maximum > 0 else 0.0

        return score, maximum
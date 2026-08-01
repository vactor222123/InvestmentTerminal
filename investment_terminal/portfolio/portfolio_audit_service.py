"""
Portfolio configuration audit service.
"""

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
)
from investment_terminal.portfolio.portfolio_audit_models import (
    PortfolioAuditIssue,
    PortfolioAuditResult,
)


class PortfolioConfigurationAuditService:
    """
    Check whether a portfolio is ready for market-value integration.

    Domain-model validation already rejects malformed holdings. This
    service reports operational readiness issues that should not make
    the portfolio file impossible to load.
    """

    def audit(
        self,
        portfolio: CurrentPortfolio,
    ) -> PortfolioAuditResult:
        if not isinstance(
            portfolio,
            CurrentPortfolio,
        ):
            raise TypeError(
                "portfolio must be a CurrentPortfolio"
            )

        issues: list[PortfolioAuditIssue] = []
        ready_count = 0

        if not portfolio.holdings:
            issues.append(
                PortfolioAuditIssue(
                    code="EMPTY_PORTFOLIO",
                    level="WARNING",
                    message=(
                        "The portfolio contains no holdings. "
                        "Add the exact owned instruments before "
                        "market-value analysis."
                    ),
                )
            )

        for holding in portfolio.holdings:
            market_data_ready = True

            if holding.exchange_ticker is None:
                market_data_ready = False
                issues.append(
                    PortfolioAuditIssue(
                        code="MISSING_MARKET_TICKER",
                        level="WARNING",
                        symbol=holding.symbol,
                        message=(
                            "No exchange_ticker is configured. "
                            "Automatic market-price lookup is not "
                            "ready for this holding."
                        ),
                    )
                )

            if (
                holding.currency
                != portfolio.policy.base_currency
            ):
                issues.append(
                    PortfolioAuditIssue(
                        code="FX_CONVERSION_REQUIRED",
                        level="INFO",
                        symbol=holding.symbol,
                        message=(
                            f"Holding currency {holding.currency} "
                            f"differs from portfolio base currency "
                            f"{portfolio.policy.base_currency}. "
                            "FX conversion will be required."
                        ),
                    )
                )

            if (
                holding.asset_type == "STOCK"
                and holding.isin is None
            ):
                issues.append(
                    PortfolioAuditIssue(
                        code="STOCK_ISIN_OPTIONAL",
                        level="INFO",
                        symbol=holding.symbol,
                        message=(
                            "The stock has no ISIN. This is allowed "
                            "because exchange_ticker is the primary "
                            "market-data identifier."
                        ),
                    )
                )

            if market_data_ready:
                ready_count += 1

        if (
            portfolio.cash_balance
            < portfolio.policy.monthly_contribution
            and portfolio.holdings
        ):
            issues.append(
                PortfolioAuditIssue(
                    code="CASH_BELOW_MONTHLY_CONTRIBUTION",
                    level="INFO",
                    message=(
                        "Current cash is below one configured monthly "
                        "contribution. This is informational and does "
                        "not invalidate the portfolio."
                    ),
                )
            )

        return PortfolioAuditResult(
            portfolio_name=portfolio.name,
            holding_count=len(
                portfolio.holdings
            ),
            market_data_ready_count=ready_count,
            issues=tuple(issues),
        )
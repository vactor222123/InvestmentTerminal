"""
Portfolio market-value calculation service.
"""

from datetime import datetime, timezone

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
)
from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioMarketPosition,
    PortfolioMarketValueResult,
)
from investment_terminal.portfolio.portfolio_price_provider import (
    PortfolioPriceProvider,
)


class PortfolioMarketValueService:
    """Calculate current market value from validated holdings and quotes."""

    def __init__(
        self,
        price_provider: PortfolioPriceProvider,
    ) -> None:
        self.price_provider = price_provider

    def calculate(
        self,
        portfolio: CurrentPortfolio,
        *,
        generated_at: datetime | None = None,
    ) -> PortfolioMarketValueResult:
        if not isinstance(
            portfolio,
            CurrentPortfolio,
        ):
            raise TypeError(
                "portfolio must be a CurrentPortfolio"
            )

        positions = tuple(
            self._build_position(
                holding
            )
            for holding in portfolio.holdings
        )

        return PortfolioMarketValueResult(
            portfolio_name=portfolio.name,
            base_currency=(
                portfolio.policy.base_currency
            ),
            generated_at=(
                generated_at
                if generated_at is not None
                else datetime.now(timezone.utc)
            ),
            positions=positions,
            cash_value=portfolio.cash_balance,
        )

    def _build_position(
        self,
        holding,
    ) -> PortfolioMarketPosition:
        if holding.exchange_ticker is None:
            raise ValueError(
                f"{holding.symbol} has no exchange_ticker "
                "for market-price lookup"
            )

        quote = self.price_provider.get_quote(
            instrument_key=holding.instrument_key,
            exchange_ticker=holding.exchange_ticker,
        )

        return PortfolioMarketPosition.build(
            holding,
            quote,
        )
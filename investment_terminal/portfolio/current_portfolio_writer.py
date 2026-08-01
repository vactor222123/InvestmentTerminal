"""
Write imported holdings into the current portfolio JSON.
"""

import json
from dataclasses import replace
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_loader import (
    CurrentPortfolioLoader,
)
from investment_terminal.portfolio.portfolio_holding_import_models import (
    PortfolioHoldingImportResult,
)


class CurrentPortfolioWriter:
    """Persist validated holdings into a current portfolio JSON file."""

    @classmethod
    def replace_holdings(
        cls,
        *,
        portfolio_path: str | Path,
        import_result: PortfolioHoldingImportResult,
        output_path: str | Path | None = None,
    ) -> Path:
        if not isinstance(
            import_result,
            PortfolioHoldingImportResult,
        ):
            raise TypeError(
                "import_result must be a "
                "PortfolioHoldingImportResult"
            )

        source_path = (
            portfolio_path
            if isinstance(portfolio_path, Path)
            else Path(portfolio_path)
        )
        destination = (
            output_path
            if isinstance(output_path, Path)
            else (
                Path(output_path)
                if output_path is not None
                else source_path
            )
        )

        portfolio = CurrentPortfolioLoader.load(
            source_path
        )
        updated = replace(
            portfolio,
            holdings=import_result.holdings,
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination.write_text(
            json.dumps(
                updated.to_dict(),
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        return destination
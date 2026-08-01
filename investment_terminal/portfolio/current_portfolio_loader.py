"""
JSON loader for the user's current portfolio.
"""

import json
from pathlib import Path

from investment_terminal.portfolio.current_portfolio_models import (
    CurrentPortfolio,
    PortfolioHolding,
    PortfolioPolicy,
)


class CurrentPortfolioLoader:
    """Load and validate one current-portfolio JSON file."""

    DEFAULT_PATH = (
        Path("data")
        / "portfolios"
        / "current_portfolio.json"
    )

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_PATH,
    ) -> CurrentPortfolio:
        resolved_path = (
            path
            if isinstance(path, Path)
            else Path(path)
        )

        if not resolved_path.exists():
            raise FileNotFoundError(
                "Current portfolio file does not exist: "
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise ValueError(
                "Current portfolio path must point to a file"
            )

        try:
            payload = json.loads(
                resolved_path.read_text(
                    encoding="utf-8",
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Current portfolio file contains invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise TypeError(
                "Current portfolio JSON root must be an object"
            )

        policy_payload = payload.get(
            "policy"
        )
        holdings_payload = payload.get(
            "holdings"
        )

        if not isinstance(
            policy_payload,
            dict,
        ):
            raise TypeError(
                "policy must be a JSON object"
            )

        if not isinstance(
            holdings_payload,
            list,
        ):
            raise TypeError(
                "holdings must be a JSON array"
            )

        policy = PortfolioPolicy(
            core_target_weight=policy_payload[
                "core_target_weight"
            ],
            tactical_target_weight=policy_payload[
                "tactical_target_weight"
            ],
            cash_target_weight=policy_payload[
                "cash_target_weight"
            ],
            monthly_contribution=policy_payload[
                "monthly_contribution"
            ],
            base_currency=policy_payload.get(
                "base_currency",
                "EUR",
            ),
        )

        holdings = tuple(
            PortfolioHolding(
                symbol=item["symbol"],
                name=item["name"],
                asset_type=item["asset_type"],
                sleeve=item["sleeve"],
                quantity=item["quantity"],
                average_cost=item["average_cost"],
                currency=item.get(
                    "currency",
                    policy.base_currency,
                ),
            )
            for item in holdings_payload
        )

        return CurrentPortfolio(
            name=payload["name"],
            policy=policy,
            holdings=holdings,
            cash_balance=payload[
                "cash_balance"
            ],
        )
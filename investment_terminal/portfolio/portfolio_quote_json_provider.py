"""
JSON-backed portfolio market-price provider.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from investment_terminal.portfolio.portfolio_market_value_models import (
    PortfolioPriceQuote,
)
from investment_terminal.portfolio.portfolio_price_provider import (
    InMemoryPortfolioPriceProvider,
)


class JsonPortfolioPriceProvider(
    InMemoryPortfolioPriceProvider
):
    """Load validated portfolio quotes from a UTF-8 JSON file."""

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "JsonPortfolioPriceProvider":
        resolved_path = (
            path
            if isinstance(path, Path)
            else Path(path)
        )

        if not resolved_path.exists():
            raise FileNotFoundError(
                "Portfolio quotes file does not exist: "
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise ValueError(
                "Portfolio quotes path must point to a file"
            )

        try:
            payload = json.loads(
                resolved_path.read_text(
                    encoding="utf-8",
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Portfolio quotes file contains invalid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "Portfolio quotes JSON root must be an object"
            )

        quote_items = payload.get(
            "quotes"
        )

        if not isinstance(
            quote_items,
            list,
        ):
            raise TypeError(
                "quotes must be a JSON array"
            )

        quotes: dict[str, PortfolioPriceQuote] = {}

        for index, item in enumerate(
            quote_items,
            start=1,
        ):
            quote = cls._build_quote(
                item,
                item_number=index,
            )

            if quote.instrument_key in quotes:
                raise ValueError(
                    "Portfolio quotes must contain unique "
                    f"instrument keys: {quote.instrument_key}"
                )

            quotes[
                quote.instrument_key
            ] = quote

        return cls(
            quotes
        )

    @staticmethod
    def _build_quote(
        item: Any,
        *,
        item_number: int,
    ) -> PortfolioPriceQuote:
        if not isinstance(
            item,
            dict,
        ):
            raise TypeError(
                f"Quote item {item_number} must be an object"
            )

        try:
            quoted_at = datetime.fromisoformat(
                item["quoted_at"]
            )

            return PortfolioPriceQuote(
                instrument_key=item[
                    "instrument_key"
                ],
                exchange_ticker=item[
                    "exchange_ticker"
                ],
                price=item["price"],
                currency=item["currency"],
                quoted_at=quoted_at,
                source=item.get(
                    "source",
                    "JSON",
                ),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"Invalid portfolio quote item "
                f"{item_number}: {exc}"
            ) from exc
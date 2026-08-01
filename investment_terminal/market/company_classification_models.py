"""
Company classification models used by sector-aware analysis.
"""

from dataclasses import dataclass
from typing import Any


SUPPORTED_BUSINESS_MODELS = (
    "STANDARD",
    "BANK",
    "PAYMENT_NETWORK",
    "INSURER",
    "REIT",
)


@dataclass(frozen=True, slots=True)
class CompanyClassification:
    """
    Sector, industry, and business-model metadata for one symbol.
    """

    symbol: str
    sector: str
    industry: str
    business_model: str = "STANDARD"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "symbol",
            self._normalize_symbol(
                self.symbol
            ),
        )
        object.__setattr__(
            self,
            "sector",
            self._normalize_text(
                self.sector,
                field_name="sector",
            ),
        )
        object.__setattr__(
            self,
            "industry",
            self._normalize_text(
                self.industry,
                field_name="industry",
            ),
        )

        model = self._normalize_text(
            self.business_model,
            field_name="business_model",
        ).upper()

        if model not in SUPPORTED_BUSINESS_MODELS:
            raise ValueError(
                "business_model must be one of: "
                + ", ".join(
                    SUPPORTED_BUSINESS_MODELS
                )
            )

        object.__setattr__(
            self,
            "business_model",
            model,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "sector": self.sector,
            "industry": self.industry,
            "business_model": self.business_model,
        }

    @staticmethod
    def _normalize_symbol(
        value: object,
    ) -> str:
        normalized = CompanyClassification._normalize_text(
            value,
            field_name="symbol",
        ).upper()

        if any(
            character.isspace()
            for character in normalized
        ):
            raise ValueError(
                "symbol must not contain whitespace"
            )

        return normalized

    @staticmethod
    def _normalize_text(
        value: object,
        *,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip()
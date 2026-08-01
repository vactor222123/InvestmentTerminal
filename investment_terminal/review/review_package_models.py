"""
Unified investment review package models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ReviewPackageSection:
    """One named JSON-ready section in the review package."""

    name: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name.strip()
        ):
            raise ValueError(
                "name must be a non-empty string"
            )

        if not isinstance(
            self.payload,
            dict,
        ):
            raise TypeError(
                "payload must be a dictionary"
            )

        object.__setattr__(
            self,
            "name",
            self.name.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class InvestmentReviewPackage:
    """
    Unified machine-generated package prepared for external analysis.

    The package intentionally separates program-generated analysis from
    later external context such as current news, politics, geopolitics,
    and macroeconomic interpretation.
    """

    schema_version: str
    generated_at: datetime
    portfolio_name: str
    sections: tuple[ReviewPackageSection, ...]
    warnings: tuple[str, ...] = ()

    REQUIRED_SECTIONS = (
        "data_freshness",
        "market_analysis",
        "portfolio",
        "stock_analysis",
        "etf_analysis",
        "watchlist",
        "opportunities",
        "machine_recommendations",
    )

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, str)
            or not self.schema_version.strip()
        ):
            raise ValueError(
                "schema_version must be a non-empty string"
            )

        if not isinstance(
            self.generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        if self.generated_at.tzinfo is None:
            raise ValueError(
                "generated_at must be timezone-aware"
            )

        if (
            not isinstance(self.portfolio_name, str)
            or not self.portfolio_name.strip()
        ):
            raise ValueError(
                "portfolio_name must be a non-empty string"
            )

        if not isinstance(
            self.sections,
            tuple,
        ):
            raise TypeError(
                "sections must be a tuple"
            )

        if any(
            not isinstance(
                section,
                ReviewPackageSection,
            )
            for section in self.sections
        ):
            raise TypeError(
                "sections must contain only ReviewPackageSection objects"
            )

        names = tuple(
            section.name
            for section in self.sections
        )

        if len(names) != len(set(names)):
            raise ValueError(
                "sections must contain unique names"
            )

        missing = tuple(
            name
            for name in self.REQUIRED_SECTIONS
            if name not in names
        )

        if missing:
            raise ValueError(
                "review package is missing required sections: "
                + ", ".join(missing)
            )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        if any(
            not isinstance(
                warning,
                str,
            )
            or not warning.strip()
            for warning in self.warnings
        ):
            raise ValueError(
                "warnings must contain only non-empty strings"
            )

    def section(
        self,
        name: str,
    ) -> ReviewPackageSection:
        normalized = name.strip()

        for section in self.sections:
            if section.name == normalized:
                return section

        raise KeyError(
            f"No review package section found for {normalized}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "portfolio_name": self.portfolio_name,
            "warnings": list(self.warnings),
            "sections": {
                section.name: section.payload
                for section in self.sections
            },
        }
"""
Portfolio configuration audit models.
"""

from dataclasses import dataclass
from typing import Any


SUPPORTED_AUDIT_LEVELS = (
    "INFO",
    "WARNING",
    "ERROR",
)


@dataclass(frozen=True, slots=True)
class PortfolioAuditIssue:
    """One portfolio configuration issue."""

    code: str
    level: str
    message: str
    symbol: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "code",
            "level",
            "message",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

            object.__setattr__(
                self,
                field_name,
                value.strip(),
            )

        normalized_level = self.level.upper()

        if normalized_level not in SUPPORTED_AUDIT_LEVELS:
            raise ValueError(
                "level must be one of: "
                + ", ".join(
                    SUPPORTED_AUDIT_LEVELS
                )
            )

        object.__setattr__(
            self,
            "level",
            normalized_level,
        )
        object.__setattr__(
            self,
            "code",
            self.code.upper(),
        )

        if self.symbol is not None:
            if (
                not isinstance(self.symbol, str)
                or not self.symbol.strip()
            ):
                raise ValueError(
                    "symbol must be a non-empty string or None"
                )

            object.__setattr__(
                self,
                "symbol",
                self.symbol.strip().upper(),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "level": self.level,
            "message": self.message,
            "symbol": self.symbol,
        }


@dataclass(frozen=True, slots=True)
class PortfolioAuditResult:
    """Complete audit result for one portfolio configuration."""

    portfolio_name: str
    holding_count: int
    market_data_ready_count: int
    issues: tuple[PortfolioAuditIssue, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.portfolio_name, str)
            or not self.portfolio_name.strip()
        ):
            raise ValueError(
                "portfolio_name must be a non-empty string"
            )

        object.__setattr__(
            self,
            "portfolio_name",
            self.portfolio_name.strip(),
        )

        for field_name in (
            "holding_count",
            "market_data_ready_count",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if self.market_data_ready_count > self.holding_count:
            raise ValueError(
                "market_data_ready_count must not exceed holding_count"
            )

        if not isinstance(
            self.issues,
            tuple,
        ):
            raise TypeError(
                "issues must be a tuple"
            )

        if any(
            not isinstance(
                issue,
                PortfolioAuditIssue,
            )
            for issue in self.issues
        ):
            raise TypeError(
                "issues must contain only PortfolioAuditIssue objects"
            )

    @property
    def error_count(self) -> int:
        return self._count_level(
            "ERROR"
        )

    @property
    def warning_count(self) -> int:
        return self._count_level(
            "WARNING"
        )

    @property
    def info_count(self) -> int:
        return self._count_level(
            "INFO"
        )

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    @property
    def is_market_data_ready(self) -> bool:
        return (
            self.holding_count > 0
            and self.market_data_ready_count
            == self.holding_count
            and self.error_count == 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_name": self.portfolio_name,
            "holding_count": self.holding_count,
            "market_data_ready_count": (
                self.market_data_ready_count
            ),
            "is_valid": self.is_valid,
            "is_market_data_ready": (
                self.is_market_data_ready
            ),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
        }

    def _count_level(
        self,
        level: str,
    ) -> int:
        return sum(
            1
            for issue in self.issues
            if issue.level == level
        )
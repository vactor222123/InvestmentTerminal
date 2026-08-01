"""
Structured data-preparation result models.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class PreparationAssetResult:
    """
    Data-preparation result for one asset.
    """

    symbol: str
    success: bool

    downloaded: int
    inserted: int
    duplicates: int

    started_at: datetime
    finished_at: datetime

    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        normalized_symbol = self._normalize_text(
            self.symbol,
            field_name="symbol",
        )

        if not isinstance(self.success, bool):
            raise TypeError(
                "success must be a bool"
            )

        for field_name in (
            "downloaded",
            "inserted",
            "duplicates",
        ):
            value = getattr(self, field_name)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be "
                    "a non-negative integer"
                )

        if not isinstance(
            self.started_at,
            datetime,
        ):
            raise TypeError(
                "started_at must be a datetime"
            )

        if not isinstance(
            self.finished_at,
            datetime,
        ):
            raise TypeError(
                "finished_at must be a datetime"
            )

        if self.finished_at < self.started_at:
            raise ValueError(
                "finished_at must not be before started_at"
            )

        if self.success:
            if (
                self.error_type is not None
                or self.error_message is not None
            ):
                raise ValueError(
                    "Successful preparation must not "
                    "contain error information"
                )
        else:
            if (
                not isinstance(self.error_type, str)
                or not self.error_type.strip()
            ):
                raise ValueError(
                    "Failed preparation requires error_type"
                )

            if (
                not isinstance(self.error_message, str)
                or not self.error_message.strip()
            ):
                raise ValueError(
                    "Failed preparation requires error_message"
                )

            object.__setattr__(
                self,
                "error_type",
                self.error_type.strip(),
            )
            object.__setattr__(
                self,
                "error_message",
                self.error_message.strip(),
            )

        object.__setattr__(
            self,
            "symbol",
            normalized_symbol,
        )

    @property
    def elapsed_seconds(self) -> float:
        """
        Return preparation duration in seconds.
        """
        return round(
            (
                self.finished_at
                - self.started_at
            ).total_seconds(),
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result to a JSON-ready dictionary.
        """
        result = asdict(self)

        result["started_at"] = (
            self.started_at.isoformat()
        )
        result["finished_at"] = (
            self.finished_at.isoformat()
        )
        result["elapsed_seconds"] = (
            self.elapsed_seconds
        )

        return result

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
    ) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        return value.strip().upper()


@dataclass(frozen=True, slots=True)
class UniversePreparationResult:
    """
    Aggregated preparation result for an asset universe.
    """

    started_at: datetime
    finished_at: datetime
    assets: tuple[PreparationAssetResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.started_at,
            datetime,
        ):
            raise TypeError(
                "started_at must be a datetime"
            )

        if not isinstance(
            self.finished_at,
            datetime,
        ):
            raise TypeError(
                "finished_at must be a datetime"
            )

        if self.finished_at < self.started_at:
            raise ValueError(
                "finished_at must not be before started_at"
            )

        if not isinstance(self.assets, tuple):
            raise TypeError(
                "assets must be a tuple"
            )

        if not self.assets:
            raise ValueError(
                "assets must not be empty"
            )

        if any(
            not isinstance(
                asset,
                PreparationAssetResult,
            )
            for asset in self.assets
        ):
            raise TypeError(
                "assets must contain only "
                "PreparationAssetResult objects"
            )

        symbols = [
            asset.symbol
            for asset in self.assets
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "assets must contain unique symbols"
            )

    @property
    def total_symbols(self) -> int:
        return len(self.assets)

    @property
    def successful_count(self) -> int:
        return sum(
            asset.success
            for asset in self.assets
        )

    @property
    def failed_count(self) -> int:
        return (
            self.total_symbols
            - self.successful_count
        )

    @property
    def total_downloaded(self) -> int:
        return sum(
            asset.downloaded
            for asset in self.assets
        )

    @property
    def total_inserted(self) -> int:
        return sum(
            asset.inserted
            for asset in self.assets
        )

    @property
    def total_duplicates(self) -> int:
        return sum(
            asset.duplicates
            for asset in self.assets
        )

    @property
    def elapsed_seconds(self) -> float:
        return round(
            (
                self.finished_at
                - self.started_at
            ).total_seconds(),
            4,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the aggregated result to JSON-ready data.
        """
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "elapsed_seconds": self.elapsed_seconds,
            "total_symbols": self.total_symbols,
            "successful_count": self.successful_count,
            "failed_count": self.failed_count,
            "total_downloaded": self.total_downloaded,
            "total_inserted": self.total_inserted,
            "total_duplicates": self.total_duplicates,
            "assets": [
                asset.to_dict()
                for asset in self.assets
            ],
        }
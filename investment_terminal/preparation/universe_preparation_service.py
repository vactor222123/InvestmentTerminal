"""
Prepare historical data for an asset universe.
"""

from collections.abc import Callable
from datetime import datetime, timezone

from investment_terminal.preparation.preparation_models import (
    PreparationAssetResult,
    UniversePreparationResult,
)
from investment_terminal.preparation.single_asset_preparation_service import (
    SingleAssetPreparationService,
)


class UniversePreparationService:
    """
    Prepare historical data for multiple unique assets.
    """

    def __init__(
        self,
        asset_service: SingleAssetPreparationService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.asset_service = asset_service
        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

    def prepare(
        self,
        symbols: list[str] | tuple[str, ...],
        resolution: str,
        start: datetime,
        end: datetime,
        currency: str = "USD",
        continue_on_error: bool = True,
    ) -> UniversePreparationResult:
        """
        Prepare all unique symbols in their original order.
        """
        normalized_symbols = self._normalize_symbols(
            symbols
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )

        self._validate_datetime(
            start,
            field_name="start",
        )
        self._validate_datetime(
            end,
            field_name="end",
        )

        if end <= start:
            raise ValueError(
                "end must be after start"
            )

        if not isinstance(
            continue_on_error,
            bool,
        ):
            raise TypeError(
                "continue_on_error must be a bool"
            )

        started_at = self._now()
        results: list[PreparationAssetResult] = []

        for symbol in normalized_symbols:
            asset_result = self.asset_service.prepare(
                symbol=symbol,
                resolution=normalized_resolution,
                start=start,
                end=end,
                currency=normalized_currency,
            )

            results.append(asset_result)

            if (
                not asset_result.success
                and not continue_on_error
            ):
                raise RuntimeError(
                    f"Preparation failed for "
                    f"{asset_result.symbol}: "
                    f"{asset_result.error_type}: "
                    f"{asset_result.error_message}"
                )

        finished_at = self._now()

        return UniversePreparationResult(
            started_at=started_at,
            finished_at=finished_at,
            assets=tuple(results),
        )

    def _now(self) -> datetime:
        value = self._clock()

        if not isinstance(value, datetime):
            raise TypeError(
                "clock must return a datetime"
            )

        return value

    @classmethod
    def _normalize_symbols(
        cls,
        symbols: list[str] | tuple[str, ...],
    ) -> tuple[str, ...]:
        if not isinstance(
            symbols,
            (list, tuple),
        ):
            raise TypeError(
                "symbols must be a list or tuple"
            )

        if not symbols:
            raise ValueError(
                "symbols must not be empty"
            )

        result: list[str] = []
        seen: set[str] = set()

        for symbol in symbols:
            normalized = cls._normalize_text(
                symbol,
                field_name="symbol",
            )

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(normalized)

        return tuple(result)

    @staticmethod
    def _validate_datetime(
        value: object,
        field_name: str,
    ) -> None:
        if not isinstance(value, datetime):
            raise TypeError(
                f"{field_name} must be a datetime"
            )

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
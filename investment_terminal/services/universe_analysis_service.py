"""
Multi-asset universe analysis service.
"""

from dataclasses import dataclass
from pathlib import Path

from investment_terminal.exporters.analysis_exporter import (
    AnalysisExportPackage,
)
from investment_terminal.services.analysis_orchestrator import (
    AnalysisOrchestrator,
)


@dataclass(frozen=True, slots=True)
class UniverseAnalysisFailure:
    """
    One failed asset analysis.
    """

    symbol: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class UniverseAnalysisResult:
    """
    Result of analyzing a collection of assets.
    """

    requested_symbols: tuple[str, ...]
    successful_packages: tuple[
        AnalysisExportPackage,
        ...
    ]
    failures: tuple[
        UniverseAnalysisFailure,
        ...
    ]

    @property
    def successful_count(self) -> int:
        return len(self.successful_packages)

    @property
    def failed_count(self) -> int:
        return len(self.failures)

    @property
    def total_count(self) -> int:
        return len(self.requested_symbols)


class UniverseAnalysisService:
    """
    Run the complete analysis pipeline for multiple symbols.
    """

    def __init__(
        self,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        self.orchestrator = orchestrator

    def analyze(
        self,
        symbols: list[str] | tuple[str, ...],
        resolution: str = "D",
        currency: str = "USD",
        output_dir: str | Path = "output",
        continue_on_error: bool = True,
    ) -> UniverseAnalysisResult:
        """
        Analyze all unique symbols in their original order.

        When continue_on_error is True, failures are recorded and the
        remaining assets are still processed.
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

        successful_packages: list[
            AnalysisExportPackage
        ] = []
        failures: list[
            UniverseAnalysisFailure
        ] = []

        for symbol in normalized_symbols:
            try:
                run_result = self.orchestrator.run(
                    symbol=symbol,
                    resolution=normalized_resolution,
                    currency=normalized_currency,
                    output_dir=output_dir,
                )
            except Exception as exc:
                if not continue_on_error:
                    raise

                failures.append(
                    UniverseAnalysisFailure(
                        symbol=symbol,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
                continue

            successful_packages.append(
                run_result.package
            )

        return UniverseAnalysisResult(
            requested_symbols=normalized_symbols,
            successful_packages=tuple(
                successful_packages
            ),
            failures=tuple(failures),
        )

    @classmethod
    def _normalize_symbols(
        cls,
        symbols: list[str] | tuple[str, ...],
    ) -> tuple[str, ...]:
        """
        Validate, normalize and deduplicate symbols.
        """
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

        for value in symbols:
            normalized = cls._normalize_text(
                value,
                field_name="symbol",
            )

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(normalized)

        if not result:
            raise ValueError(
                "symbols must contain at least one symbol"
            )

        return tuple(result)

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
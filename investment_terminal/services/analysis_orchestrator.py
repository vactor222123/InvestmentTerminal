"""
End-to-end investment analysis orchestration.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.clients.fundamental_data_client import (
    FundamentalDataClient,
)
from investment_terminal.decision_engine.decision_engine import (
    DecisionEngine,
)
from investment_terminal.exporters.analysis_exporter import (
    AnalysisExportPackage,
    AnalysisExporter,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreService,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisService,
)
from investment_terminal.services.technical_score_service import (
    TechnicalScoreService,
)


@dataclass(frozen=True, slots=True)
class AnalysisRunResult:
    """
    Result of one complete analysis run.
    """

    package: AnalysisExportPackage
    output_path: Path


class AnalysisOrchestrator:
    """
    Run technical, fundamental and decision analysis,
    then export one JSON package.
    """

    def __init__(
        self,
        technical_analysis_service: TechnicalAnalysisService,
        technical_score_service: TechnicalScoreService,
        fundamental_client: FundamentalDataClient,
        fundamental_score_service: FundamentalScoreService,
        decision_engine: DecisionEngine,
        exporter: AnalysisExporter,
    ) -> None:
        self.technical_analysis_service = (
            technical_analysis_service
        )
        self.technical_score_service = (
            technical_score_service
        )
        self.fundamental_client = fundamental_client
        self.fundamental_score_service = (
            fundamental_score_service
        )
        self.decision_engine = decision_engine
        self.exporter = exporter

    def run(
        self,
        symbol: str,
        resolution: str = "D",
        currency: str = "USD",
        output_dir: str | Path = "output",
    ) -> AnalysisRunResult:
        """
        Run the complete analysis pipeline.
        """
        normalized_symbol = self._normalize_text(
            symbol,
            field_name="symbol",
        )
        normalized_resolution = self._normalize_text(
            resolution,
            field_name="resolution",
        )
        normalized_currency = self._normalize_text(
            currency,
            field_name="currency",
        )

        technical_analysis = (
            self.technical_analysis_service.analyze(
                symbol=normalized_symbol,
                resolution=normalized_resolution,
            )
        )

        technical_score = (
            self.technical_score_service.score_analysis(
                technical_analysis
            )
        )

        fundamental_snapshot = (
            self.fundamental_client.get_fundamentals(
                symbol=normalized_symbol,
                currency=normalized_currency,
            )
        )

        fundamental_score = (
            self.fundamental_score_service.score_snapshot(
                fundamental_snapshot
            )
        )

        generated_at = datetime.now(
            timezone.utc
        )

        decision = self.decision_engine.evaluate(
            technical_analysis=technical_analysis,
            technical_score=technical_score,
            fundamental_snapshot=fundamental_snapshot,
            fundamental_score=fundamental_score,
            generated_at=generated_at,
        )

        package = self.exporter.build_package(
            technical_analysis=technical_analysis,
            technical_score=technical_score,
            fundamental_snapshot=fundamental_snapshot,
            fundamental_score=fundamental_score,
            decision=decision,
            generated_at=generated_at,
        )

        output_path = (
            Path(output_dir)
            / f"{normalized_symbol}_analysis.json"
        )

        saved_path = self.exporter.save_json(
            package=package,
            output_path=output_path,
        )

        return AnalysisRunResult(
            package=package,
            output_path=saved_path,
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
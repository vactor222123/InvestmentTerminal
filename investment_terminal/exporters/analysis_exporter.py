"""
Combined technical, fundamental and decision analysis exporter.
"""

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from investment_terminal.decision_engine.decision_model import (
    DecisionResult,
)
from investment_terminal.models.fundamental_snapshot import (
    FundamentalSnapshot,
)
from investment_terminal.services.fundamental_score_service import (
    FundamentalScoreResult,
)
from investment_terminal.services.technical_analysis_service import (
    TechnicalAnalysisResult,
)
from investment_terminal.services.technical_score_service import (
    TechnicalScoreResult,
)
from investment_terminal.utils.atomic_write import (
    write_text_atomic,
)


@dataclass(frozen=True, slots=True)
class AnalysisDataQualitySummary:
    """
    Combined data-quality summary.
    """

    technical_percent: float
    fundamental_percent: float
    overall_percent: float

    technical_missing: tuple[str, ...]
    fundamental_missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisExportPackage:
    """
    Complete analysis package for one asset.
    """

    schema_version: str
    generated_at: datetime
    symbol: str
    currency: str

    technical_analysis: TechnicalAnalysisResult
    technical_score: TechnicalScoreResult

    fundamental_snapshot: FundamentalSnapshot
    fundamental_score: FundamentalScoreResult

    decision: DecisionResult

    data_quality: AnalysisDataQualitySummary

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the package into a JSON-ready dictionary.
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at.isoformat(),
            "symbol": self.symbol,
            "currency": self.currency,
            "technical": {
                "analysis": _to_json_ready(
                    self.technical_analysis
                ),
                "score": _to_json_ready(
                    self.technical_score
                ),
            },
            "fundamental": {
                "snapshot": (
                    self.fundamental_snapshot.to_dict()
                ),
                "score": (
                    self.fundamental_score.to_dict()
                ),
            },
            "decision": self.decision.to_dict(),
            "data_quality": _to_json_ready(
                self.data_quality
            ),
        }


class AnalysisExporter:
    """
    Build and save combined analysis packages.
    """

    SCHEMA_VERSION = "1.0"

    def build_package(
        self,
        technical_analysis: TechnicalAnalysisResult,
        technical_score: TechnicalScoreResult,
        fundamental_snapshot: FundamentalSnapshot,
        fundamental_score: FundamentalScoreResult,
        decision: DecisionResult,
        generated_at: datetime,
    ) -> AnalysisExportPackage:
        """
        Validate and combine analysis components.
        """
        self._validate_components(
            technical_analysis=technical_analysis,
            technical_score=technical_score,
            fundamental_snapshot=fundamental_snapshot,
            fundamental_score=fundamental_score,
            decision=decision,
            generated_at=generated_at,
        )

        technical_quality = (
            technical_analysis
            .data_quality
            .completeness_percent
        )

        fundamental_quality = (
            fundamental_snapshot.data_quality
            .completeness_percent
            if fundamental_snapshot.data_quality
            is not None
            else 0.0
        )

        overall_quality = (
            technical_quality
            + fundamental_quality
        ) / 2.0

        quality_summary = AnalysisDataQualitySummary(
            technical_percent=round(
                technical_quality,
                2,
            ),
            fundamental_percent=round(
                fundamental_quality,
                2,
            ),
            overall_percent=round(
                overall_quality,
                2,
            ),
            technical_missing=(
                technical_analysis
                .data_quality
                .missing_indicators
            ),
            fundamental_missing=(
                fundamental_snapshot
                .data_quality
                .missing_fields
                if fundamental_snapshot.data_quality
                is not None
                else fundamental_snapshot
                .metric_field_names()
            ),
        )

        return AnalysisExportPackage(
            schema_version=self.SCHEMA_VERSION,
            generated_at=generated_at,
            symbol=technical_analysis.symbol,
            currency=technical_analysis.currency,
            technical_analysis=technical_analysis,
            technical_score=technical_score,
            fundamental_snapshot=fundamental_snapshot,
            fundamental_score=fundamental_score,
            decision=decision,
            data_quality=quality_summary,
        )

    def save_json(
        self,
        package: AnalysisExportPackage,
        output_path: str | Path,
    ) -> Path:
        """
        Save an analysis package as formatted JSON.
        """
        if not isinstance(
            package,
            AnalysisExportPackage,
        ):
            raise TypeError(
                "package must be an AnalysisExportPackage"
            )

        path = Path(output_path)

        if path.suffix.lower() != ".json":
            raise ValueError(
                "output_path must use the .json extension"
            )

        payload = json.dumps(
            package.to_dict(),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

        return write_text_atomic(
            path,
            payload,
            encoding="utf-8",
        )

    @staticmethod
    def _validate_components(
        technical_analysis: TechnicalAnalysisResult,
        technical_score: TechnicalScoreResult,
        fundamental_snapshot: FundamentalSnapshot,
        fundamental_score: FundamentalScoreResult,
        decision: DecisionResult,
        generated_at: datetime,
    ) -> None:
        """
        Ensure all components belong to the same asset.
        """
        if not isinstance(
            technical_analysis,
            TechnicalAnalysisResult,
        ):
            raise TypeError(
                "technical_analysis must be "
                "a TechnicalAnalysisResult"
            )

        if not isinstance(
            technical_score,
            TechnicalScoreResult,
        ):
            raise TypeError(
                "technical_score must be "
                "a TechnicalScoreResult"
            )

        if not isinstance(
            fundamental_snapshot,
            FundamentalSnapshot,
        ):
            raise TypeError(
                "fundamental_snapshot must be "
                "a FundamentalSnapshot"
            )

        if not isinstance(
            fundamental_score,
            FundamentalScoreResult,
        ):
            raise TypeError(
                "fundamental_score must be "
                "a FundamentalScoreResult"
            )

        if not isinstance(
            decision,
            DecisionResult,
        ):
            raise TypeError(
                "decision must be a DecisionResult"
            )

        if not isinstance(
            generated_at,
            datetime,
        ):
            raise TypeError(
                "generated_at must be a datetime"
            )

        symbols = {
            technical_analysis.symbol,
            technical_score.symbol,
            fundamental_snapshot.symbol,
            fundamental_score.symbol,
            decision.symbol,
        }

        if len(symbols) != 1:
            raise ValueError(
                "All analysis components must use "
                "the same symbol"
            )

        if (
            technical_analysis.currency
            != fundamental_snapshot.currency
            or fundamental_snapshot.currency
            != fundamental_score.currency
            or fundamental_score.currency
            != decision.currency
        ):
            raise ValueError(
                "Analysis components use "
                "different currencies"
            )

        if (
            technical_analysis.resolution
            != technical_score.resolution
        ):
            raise ValueError(
                "Technical components use "
                "different resolutions"
            )


def _to_json_ready(
    value: Any,
) -> Any:
    """
    Recursively convert dataclasses and special values
    into JSON-compatible Python objects.
    """
    if isinstance(value, datetime):
        return value.isoformat()

    if is_dataclass(value):
        return _to_json_ready(
            asdict(value)
        )

    if isinstance(value, dict):
        return {
            str(key): _to_json_ready(item)
            for key, item in value.items()
        }

    if isinstance(value, tuple):
        return [
            _to_json_ready(item)
            for item in value
        ]

    if isinstance(value, list):
        return [
            _to_json_ready(item)
            for item in value
        ]

    return value

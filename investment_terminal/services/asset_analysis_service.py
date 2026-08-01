"""
High-level service that performs the complete analysis pipeline
for a single asset.
"""

from datetime import datetime, timezone

from investment_terminal.clients.fundamental_data_client import (
    FundamentalDataClient,
)
from investment_terminal.decision_engine.decision_engine import (
    DecisionEngine,
)
from investment_terminal.decision_engine.decision_model import (
    DecisionResult,
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


class AssetAnalysisService:
    """
    Execute the complete analysis pipeline for one asset.
    """

    def __init__(
        self,
        technical_analysis_service: TechnicalAnalysisService,
        fundamental_client: FundamentalDataClient,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self.technical_analysis_service = (
            technical_analysis_service
        )

        self.fundamental_client = (
            fundamental_client
        )

        self.technical_score_service = (
            TechnicalScoreService(
                technical_analysis_service
            )
        )

        self.fundamental_score_service = (
            FundamentalScoreService(
                fundamental_client
            )
        )

        self.decision_engine = (
            decision_engine
            if decision_engine is not None
            else DecisionEngine()
        )

    def analyze(
        self,
        symbol: str,
        resolution: str = "D",
        currency: str = "USD",
    ) -> DecisionResult:
        """
        Perform a complete investment analysis.
        """
        technical_analysis = (
            self.technical_analysis_service.analyze(
                symbol=symbol,
                resolution=resolution,
            )
        )

        technical_score = (
            self.technical_score_service.score_analysis(
                technical_analysis
            )
        )

        fundamental_snapshot = (
            self.fundamental_client.get_fundamentals(
                symbol=symbol,
                currency=currency,
            )
        )

        fundamental_score = (
            self.fundamental_score_service.score_snapshot(
                fundamental_snapshot
            )
        )

        return self.decision_engine.evaluate(
            technical_analysis=technical_analysis,
            technical_score=technical_score,
            fundamental_snapshot=fundamental_snapshot,
            fundamental_score=fundamental_score,
            generated_at=datetime.now(
                timezone.utc
            ),
        )
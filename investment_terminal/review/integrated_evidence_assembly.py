"""Typed assembly boundary for integrated investment-review evidence."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.analysis.current_state_market_analysis import (
    CurrentStateEquityAnalysisResult,
    require_current_state_equity_analysis_result,
)
from investment_terminal.context.external_context_models import (
    ExternalContextEvidence,
)
from investment_terminal.context.external_context_sentiment import (
    ExternalContextSentimentEvidence,
)
from investment_terminal.portfolio.portfolio_snapshot_models import (
    PortfolioSnapshot,
)
from investment_terminal.universe.etf_discovery import (
    ETFDiscoveryEvidence,
)
from investment_terminal.universe.screening_pipeline import (
    ScreeningResult,
)
from investment_terminal.universe.sector_analysis import (
    SectorAnalysisEvidence,
)
from investment_terminal.utils.validation import (
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class IntegratedInvestmentReviewEvidence:
    """Immutable typed evidence collected before Review Package generation."""

    schema_version: str
    assembled_at: datetime
    portfolio: PortfolioSnapshot
    current_state_market: CurrentStateEquityAnalysisResult
    external_context: tuple[ExternalContextEvidence, ...] = ()
    context_sentiment: tuple[ExternalContextSentimentEvidence, ...] = ()
    etf_discovery: ETFDiscoveryEvidence | None = None
    sector_analysis: SectorAnalysisEvidence | None = None
    screening: ScreeningResult | None = None

    SCHEMA_VERSION: ClassVar[str] = "1.0"
    OPTIONAL_EVIDENCE_ORDER: ClassVar[tuple[str, ...]] = (
        "EXTERNAL_CONTEXT",
        "ETF_DISCOVERY",
        "SECTOR_ANALYSIS",
        "SCREENING",
    )

    def __post_init__(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError(
                "unsupported integrated evidence schema_version: "
                f"{self.schema_version}"
            )
        validate_aware_datetime(
            self.assembled_at,
            field_name="assembled_at",
        )
        if not isinstance(
            self.portfolio,
            PortfolioSnapshot,
        ):
            raise TypeError(
                "portfolio must be a PortfolioSnapshot"
            )

        require_current_state_equity_analysis_result(
            self.current_state_market
        )
        validate_aware_datetime(
            self.current_state_market.generated_at,
            field_name="current_state_market.generated_at",
        )
        if (
            self.current_state_market.generated_at
            > self.assembled_at
        ):
            raise ValueError(
                "current_state_market cannot be later than assembled_at"
            )

        context = self._normalize_context(
            self.external_context
        )
        sentiment = self._normalize_sentiment(
            self.context_sentiment,
            context=context,
        )
        object.__setattr__(
            self,
            "external_context",
            context,
        )
        object.__setattr__(
            self,
            "context_sentiment",
            sentiment,
        )

        self._validate_optional_evidence()
        self._validate_universe_identity()

    @property
    def missing_evidence(self) -> tuple[str, ...]:
        availability = {
            "EXTERNAL_CONTEXT": bool(
                self.external_context
            ),
            "ETF_DISCOVERY": (
                self.etf_discovery is not None
            ),
            "SECTOR_ANALYSIS": (
                self.sector_analysis is not None
            ),
            "SCREENING": self.screening is not None,
        }
        return tuple(
            evidence_name
            for evidence_name in self.OPTIONAL_EVIDENCE_ORDER
            if not availability[
                evidence_name
            ]
        )

    @property
    def coverage_status(self) -> str:
        if not self.missing_evidence:
            return "COMPLETE"
        return "PARTIAL"

    @property
    def universe_key(self) -> str | None:
        for evidence in (
            self.etf_discovery,
            self.sector_analysis,
            self.screening,
        ):
            if evidence is not None:
                return evidence.universe.universe.universe_key
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-ready evidence aggregate, not Review JSON."""
        return {
            "schema_version": self.schema_version,
            "assembled_at": self.assembled_at.isoformat(),
            "coverage_status": self.coverage_status,
            "missing_evidence": list(
                self.missing_evidence
            ),
            "portfolio": self.portfolio.to_dict(),
            "current_state_market": (
                self.current_state_market.to_dict()
            ),
            "external_context": [
                evidence.to_dict()
                for evidence in self.external_context
            ],
            "context_sentiment": [
                evidence.to_dict()
                for evidence in self.context_sentiment
            ],
            "etf_discovery": (
                None
                if self.etf_discovery is None
                else self.etf_discovery.to_dict()
            ),
            "sector_analysis": (
                None
                if self.sector_analysis is None
                else self.sector_analysis.to_dict()
            ),
            "screening": (
                None
                if self.screening is None
                else self.screening.to_dict()
            ),
        }

    def _normalize_context(
        self,
        value: object,
    ) -> tuple[ExternalContextEvidence, ...]:
        if not isinstance(
            value,
            tuple,
        ):
            raise TypeError(
                "external_context must be a tuple"
            )
        if any(
            not isinstance(
                evidence,
                ExternalContextEvidence,
            )
            for evidence in value
        ):
            raise TypeError(
                "external_context must contain only "
                "ExternalContextEvidence objects"
            )

        ordered = tuple(
            sorted(
                value,
                key=lambda evidence: (
                    evidence.provenance.published_at,
                    evidence.record.context_id,
                ),
            )
        )
        identities = tuple(
            evidence.record.context_id
            for evidence in ordered
        )
        if len(identities) != len(
            set(identities)
        ):
            raise ValueError(
                "external_context must have unique context_id values"
            )
        for evidence in ordered:
            if max(
                evidence.provenance.published_at,
                evidence.provenance.fetched_at,
                evidence.quality.checked_at,
            ) > self.assembled_at:
                raise ValueError(
                    "external_context cannot be later than assembled_at"
                )
        return ordered

    def _normalize_sentiment(
        self,
        value: object,
        *,
        context: tuple[ExternalContextEvidence, ...],
    ) -> tuple[ExternalContextSentimentEvidence, ...]:
        if not isinstance(
            value,
            tuple,
        ):
            raise TypeError(
                "context_sentiment must be a tuple"
            )
        if any(
            not isinstance(
                evidence,
                ExternalContextSentimentEvidence,
            )
            for evidence in value
        ):
            raise TypeError(
                "context_sentiment must contain only "
                "ExternalContextSentimentEvidence objects"
            )

        ordered = tuple(
            sorted(
                value,
                key=lambda evidence: evidence.context_id,
            )
        )
        identities = tuple(
            evidence.context_id
            for evidence in ordered
        )
        if len(identities) != len(
            set(identities)
        ):
            raise ValueError(
                "context_sentiment must have unique context_id values"
            )
        context_identities = {
            evidence.record.context_id
            for evidence in context
        }
        orphaned = tuple(
            identity
            for identity in identities
            if identity not in context_identities
        )
        if orphaned:
            raise ValueError(
                "context_sentiment contains unknown context_id: "
                + ", ".join(
                    orphaned
                )
            )
        if any(
            evidence.assessed_at > self.assembled_at
            for evidence in ordered
        ):
            raise ValueError(
                "context_sentiment cannot be later than assembled_at"
            )
        return ordered

    def _validate_optional_evidence(self) -> None:
        expected_types = (
            (
                "etf_discovery",
                self.etf_discovery,
                ETFDiscoveryEvidence,
                "assessed_at",
            ),
            (
                "sector_analysis",
                self.sector_analysis,
                SectorAnalysisEvidence,
                "assessed_at",
            ),
            (
                "screening",
                self.screening,
                ScreeningResult,
                "evaluated_at",
            ),
        )
        for (
            field_name,
            evidence,
            expected_type,
            timestamp_field,
        ) in expected_types:
            if evidence is None:
                continue
            if not isinstance(
                evidence,
                expected_type,
            ):
                raise TypeError(
                    f"{field_name} must be "
                    f"{expected_type.__name__} or None"
                )
            if getattr(
                evidence,
                timestamp_field,
            ) > self.assembled_at:
                raise ValueError(
                    f"{field_name} cannot be later than assembled_at"
                )

    def _validate_universe_identity(self) -> None:
        universe_keys = tuple(
            evidence.universe.universe.universe_key
            for evidence in (
                self.etf_discovery,
                self.sector_analysis,
                self.screening,
            )
            if evidence is not None
        )
        if len(
            set(universe_keys)
        ) > 1:
            raise ValueError(
                "discovery evidence must reference one universe identity"
            )


class IntegratedInvestmentReviewEvidenceAssembler:
    """Assemble validated upstream results without calculating new evidence."""

    @staticmethod
    def assemble(
        *,
        assembled_at: datetime,
        portfolio: PortfolioSnapshot,
        current_state_market: CurrentStateEquityAnalysisResult,
        external_context: tuple[ExternalContextEvidence, ...] = (),
        context_sentiment: tuple[
            ExternalContextSentimentEvidence,
            ...,
        ] = (),
        etf_discovery: ETFDiscoveryEvidence | None = None,
        sector_analysis: SectorAnalysisEvidence | None = None,
        screening: ScreeningResult | None = None,
    ) -> IntegratedInvestmentReviewEvidence:
        return IntegratedInvestmentReviewEvidence(
            schema_version=(
                IntegratedInvestmentReviewEvidence.SCHEMA_VERSION
            ),
            assembled_at=assembled_at,
            portfolio=portfolio,
            current_state_market=current_state_market,
            external_context=external_context,
            context_sentiment=context_sentiment,
            etf_discovery=etf_discovery,
            sector_analysis=sector_analysis,
            screening=screening,
        )

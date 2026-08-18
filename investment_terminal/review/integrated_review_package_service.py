"""Generate and export Review Packages from integrated typed evidence."""

from dataclasses import dataclass
from pathlib import Path

from investment_terminal.review.external_context_review_adapter import (
    ExternalContextReviewAdapter,
)
from investment_terminal.review.integrated_evidence_assembly import (
    IntegratedInvestmentReviewEvidence,
)
from investment_terminal.review.portfolio_analysis_review_adapter import (
    PortfolioAnalysisReviewAdapter,
)
from investment_terminal.review.portfolio_review_adapter import (
    PortfolioReviewAdapter,
)
from investment_terminal.review.review_package_builder import (
    InvestmentReviewPackageBuilder,
)
from investment_terminal.review.review_package_exporter import (
    InvestmentReviewPackageExporter,
)
from investment_terminal.review.review_package_models import (
    InvestmentReviewPackage,
)


@dataclass(frozen=True, slots=True)
class IntegratedReviewPackageExportResult:
    """One generated package and its atomically replaced output path."""

    package: InvestmentReviewPackage
    output_path: Path

    def __post_init__(self) -> None:
        if not isinstance(
            self.package,
            InvestmentReviewPackage,
        ):
            raise TypeError(
                "package must be an InvestmentReviewPackage"
            )
        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be a Path"
            )


class IntegratedReviewPackageService:
    """Project validated evidence without recalculating upstream analysis."""

    _MISSING_WARNINGS = {
        "EXTERNAL_CONTEXT": (
            "External context evidence is not available."
        ),
        "ETF_DISCOVERY": (
            "ETF discovery evidence is not available."
        ),
        "SECTOR_ANALYSIS": (
            "Sector analysis evidence is not available."
        ),
        "SCREENING": (
            "Screening evidence is not available."
        ),
    }

    @classmethod
    def generate(
        cls,
        evidence: IntegratedInvestmentReviewEvidence,
    ) -> InvestmentReviewPackage:
        if not isinstance(
            evidence,
            IntegratedInvestmentReviewEvidence,
        ):
            raise TypeError(
                "evidence must be an "
                "IntegratedInvestmentReviewEvidence"
            )

        stock_sections = PortfolioAnalysisReviewAdapter().adapt(
            evidence.current_state_market.to_dict()
        )
        stock_sections[
            "market_analysis"
        ]["integrated_evidence"] = {
            "schema_version": evidence.schema_version,
            "assembled_at": evidence.assembled_at.isoformat(),
            "coverage_status": evidence.coverage_status,
            "missing_evidence": list(
                evidence.missing_evidence
            ),
        }
        stock_sections[
            "market_analysis"
        ]["market_discovery"] = cls._market_discovery(
            evidence
        )

        external_context = ExternalContextReviewAdapter.adapt(
            evidence.external_context,
            sentiment=evidence.context_sentiment,
        )
        warnings = cls._warnings(
            evidence,
            external_context_warnings=tuple(
                external_context["warnings"]
            ),
        )

        return InvestmentReviewPackageBuilder().build(
            portfolio_name=evidence.portfolio.portfolio_name,
            data_freshness=stock_sections[
                "data_freshness"
            ],
            market_analysis=stock_sections[
                "market_analysis"
            ],
            portfolio=PortfolioReviewAdapter().adapt(
                snapshot=evidence.portfolio,
                market_value=None,
                quotes_source=None,
            ),
            stock_analysis=stock_sections[
                "stock_analysis"
            ],
            etf_analysis=cls._etf_analysis(
                evidence
            ),
            watchlist={
                "status": "NO_EVIDENCE",
                "items": [],
            },
            opportunities=stock_sections[
                "opportunities"
            ],
            machine_recommendations=stock_sections[
                "machine_recommendations"
            ],
            external_context=external_context,
            generated_at=evidence.assembled_at,
            warnings=warnings,
        )

    @classmethod
    def generate_and_export(
        cls,
        evidence: IntegratedInvestmentReviewEvidence,
        output_path: str | Path,
    ) -> IntegratedReviewPackageExportResult:
        package = cls.generate(
            evidence
        )
        path = InvestmentReviewPackageExporter().export(
            package,
            output_path,
        )
        return IntegratedReviewPackageExportResult(
            package=package,
            output_path=path,
        )

    @staticmethod
    def _etf_analysis(
        evidence: IntegratedInvestmentReviewEvidence,
    ) -> dict:
        if evidence.etf_discovery is None:
            return {
                "status": "NO_EVIDENCE",
                "evidence": None,
            }
        return {
            "status": "CONNECTED",
            "evidence": evidence.etf_discovery.to_dict(),
            "recommendation_authorized": False,
        }

    @staticmethod
    def _market_discovery(
        evidence: IntegratedInvestmentReviewEvidence,
    ) -> dict:
        missing = tuple(
            name
            for name in (
                "SECTOR_ANALYSIS",
                "SCREENING",
            )
            if name in evidence.missing_evidence
        )
        return {
            "status": (
                "COMPLETE"
                if not missing
                else "PARTIAL"
            ),
            "universe_key": evidence.universe_key,
            "missing_evidence": list(
                missing
            ),
            "sector_analysis": (
                None
                if evidence.sector_analysis is None
                else evidence.sector_analysis.to_dict()
            ),
            "screening": (
                None
                if evidence.screening is None
                else evidence.screening.to_dict()
            ),
            "ranking_authorized": False,
            "recommendation_authorized": False,
        }

    @classmethod
    def _warnings(
        cls,
        evidence: IntegratedInvestmentReviewEvidence,
        *,
        external_context_warnings: tuple[str, ...],
    ) -> tuple[str, ...]:
        values = [
            "Portfolio market-value evidence is not included.",
            "Watchlist evidence is not included.",
        ]
        values.extend(
            cls._MISSING_WARNINGS[
                evidence_name
            ]
            for evidence_name in evidence.missing_evidence
        )
        values.extend(
            external_context_warnings
        )
        return tuple(
            dict.fromkeys(
                values
            )
        )

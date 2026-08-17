"""Deterministic portfolio drawdown analysis from validated return inputs."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import isclose
from typing import Any

from investment_terminal.portfolio.portfolio_risk_inputs import (
    PortfolioRiskInput,
    RiskDataProvenance,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
)


@dataclass(frozen=True, slots=True)
class PortfolioDrawdownPoint:
    """One compounded portfolio value and its decline from the running peak."""

    observed_at: datetime
    cumulative_growth_factor: float
    peak_growth_factor: float
    drawdown_fraction: float

    def __post_init__(self) -> None:
        validate_aware_datetime(self.observed_at, field_name="observed_at")
        cumulative = validate_finite_number(
            self.cumulative_growth_factor,
            field_name="cumulative_growth_factor",
        )
        peak = validate_finite_number(
            self.peak_growth_factor,
            field_name="peak_growth_factor",
        )
        drawdown = validate_finite_number(
            self.drawdown_fraction,
            field_name="drawdown_fraction",
        )
        if cumulative < 0:
            raise ValueError("cumulative_growth_factor must be non-negative")
        if peak <= 0:
            raise ValueError("peak_growth_factor must be greater than zero")
        if cumulative > peak:
            raise ValueError(
                "cumulative_growth_factor must not exceed peak_growth_factor"
            )
        if not -1 <= drawdown <= 0:
            raise ValueError("drawdown_fraction must be between -1 and 0")
        expected = cumulative / peak - 1
        if not isclose(drawdown, expected, rel_tol=0, abs_tol=1e-12):
            raise ValueError(
                "drawdown_fraction must match cumulative and peak growth factors"
            )
        object.__setattr__(self, "cumulative_growth_factor", cumulative)
        object.__setattr__(self, "peak_growth_factor", peak)
        object.__setattr__(self, "drawdown_fraction", drawdown)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_at": self.observed_at.isoformat(),
            "cumulative_growth_factor": self.cumulative_growth_factor,
            "peak_growth_factor": self.peak_growth_factor,
            "drawdown_fraction": self.drawdown_fraction,
        }


@dataclass(frozen=True, slots=True)
class PortfolioDrawdownAnalysis:
    """Immutable peak-to-trough evidence for one portfolio return series."""

    ledger_id: str
    portfolio_name: str
    as_of: datetime
    currency: str
    period: str
    points: tuple[PortfolioDrawdownPoint, ...]
    max_drawdown_fraction: float
    peak_at: datetime | None
    trough_at: datetime | None
    recovered_at: datetime | None
    provenance: RiskDataProvenance

    def __post_init__(self) -> None:
        for field_name in ("ledger_id", "portfolio_name"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name), field_name=field_name
                ),
            )
        validate_aware_datetime(self.as_of, field_name="as_of")
        for field_name in ("currency", "period"):
            object.__setattr__(
                self,
                field_name,
                normalize_required_text(
                    getattr(self, field_name),
                    field_name=field_name,
                    uppercase=True,
                ),
            )
        if not isinstance(self.points, tuple) or not self.points:
            raise ValueError("points must be a non-empty tuple")
        if any(not isinstance(item, PortfolioDrawdownPoint) for item in self.points):
            raise TypeError("points must contain only PortfolioDrawdownPoint objects")
        timestamps = tuple(item.observed_at for item in self.points)
        if timestamps != tuple(sorted(timestamps)):
            raise ValueError("points must be ordered by observed_at")
        if len(timestamps) != len(set(timestamps)):
            raise ValueError("points must contain unique observed_at values")
        if timestamps[-1] > self.as_of:
            raise ValueError("points must not be later than as_of")
        maximum = validate_finite_number(
            self.max_drawdown_fraction,
            field_name="max_drawdown_fraction",
        )
        if not -1 <= maximum <= 0:
            raise ValueError("max_drawdown_fraction must be between -1 and 0")
        expected = min(item.drawdown_fraction for item in self.points)
        if not isclose(maximum, expected, rel_tol=0, abs_tol=1e-12):
            raise ValueError("max_drawdown_fraction must match the drawdown points")
        object.__setattr__(self, "max_drawdown_fraction", maximum)
        self._validate_episode()
        if not isinstance(self.provenance, RiskDataProvenance):
            raise TypeError("provenance must be a RiskDataProvenance")

    def _validate_episode(self) -> None:
        episode_times = (self.peak_at, self.trough_at, self.recovered_at)
        for field_name, value in zip(
            ("peak_at", "trough_at", "recovered_at"), episode_times
        ):
            if value is not None:
                validate_aware_datetime(value, field_name=field_name)
        if self.max_drawdown_fraction == 0:
            if any(value is not None for value in episode_times):
                raise ValueError("zero drawdown must not define an episode")
            return
        if self.peak_at is None or self.trough_at is None:
            raise ValueError("negative drawdown requires peak_at and trough_at")
        if self.peak_at >= self.trough_at:
            raise ValueError("peak_at must be earlier than trough_at")
        if self.recovered_at is not None and self.recovered_at <= self.trough_at:
            raise ValueError("recovered_at must be later than trough_at")

    @property
    def recovered(self) -> bool:
        return self.recovered_at is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "portfolio_name": self.portfolio_name,
            "as_of": self.as_of.isoformat(),
            "currency": self.currency,
            "period": self.period,
            "point_count": len(self.points),
            "points": [item.to_dict() for item in self.points],
            "max_drawdown_fraction": self.max_drawdown_fraction,
            "peak_at": self.peak_at.isoformat() if self.peak_at else None,
            "trough_at": self.trough_at.isoformat() if self.trough_at else None,
            "recovered_at": (
                self.recovered_at.isoformat() if self.recovered_at else None
            ),
            "recovered": self.recovered,
            "provenance": self.provenance.to_dict(),
        }


class PortfolioDrawdownCalculator:
    """Calculate compounded portfolio drawdown without classifying risk."""

    @staticmethod
    def calculate(risk_input: PortfolioRiskInput) -> PortfolioDrawdownAnalysis:
        if not isinstance(risk_input, PortfolioRiskInput):
            raise TypeError("risk_input must be a PortfolioRiskInput")
        series = risk_input.portfolio_returns
        cumulative = Decimal("1")
        peak = Decimal("1")
        peak_at = series.started_at
        points: list[PortfolioDrawdownPoint] = []
        worst = Decimal("0")
        worst_peak_at: datetime | None = None
        trough_at: datetime | None = None
        worst_peak = Decimal("1")
        trough_index: int | None = None
        for index, observation in enumerate(series.observations):
            cumulative *= Decimal("1") + Decimal(str(observation.return_fraction))
            if cumulative > peak:
                peak = cumulative
                peak_at = observation.period_ended_at
            drawdown = cumulative / peak - Decimal("1")
            points.append(
                PortfolioDrawdownPoint(
                    observed_at=observation.period_ended_at,
                    cumulative_growth_factor=float(cumulative),
                    peak_growth_factor=float(peak),
                    drawdown_fraction=float(drawdown),
                )
            )
            if drawdown < worst:
                worst = drawdown
                worst_peak_at = peak_at
                worst_peak = peak
                trough_at = observation.period_ended_at
                trough_index = index

        recovered_at = None
        if trough_index is not None:
            for point in points[trough_index + 1 :]:
                if Decimal(str(point.cumulative_growth_factor)) >= worst_peak:
                    recovered_at = point.observed_at
                    break
        return PortfolioDrawdownAnalysis(
            ledger_id=risk_input.ledger_id,
            portfolio_name=risk_input.portfolio_name,
            as_of=risk_input.as_of,
            currency=series.currency,
            period=series.period,
            points=tuple(points),
            max_drawdown_fraction=float(worst),
            peak_at=worst_peak_at,
            trough_at=trough_at,
            recovered_at=recovered_at,
            provenance=series.provenance,
        )

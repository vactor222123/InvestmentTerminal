"""Explicit split-only share-basis projections; never rewrite source candles."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from hashlib import sha256
import math
import re
from zoneinfo import ZoneInfo

from investment_terminal.market.corporate_actions import CorporateActionSnapshot, canonical_bytes
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime, validate_finite_number


def checksum(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Invalid evidence checksum")
    return value


def finite_float(value: Fraction) -> float:
    result = float(value)
    if not math.isfinite(result) or value != 0 and result == 0:
        raise ValueError("Unrepresentable split projection")
    return result


@dataclass(frozen=True, slots=True)
class SplitPlan:
    """Observed split schedule to the snapshot's exclusive end, not completeness."""

    snapshot: CorporateActionSnapshot
    source_sha256: str
    evaluated_at: datetime
    maximum_age_days: int

    def __post_init__(self):
        if not isinstance(self.snapshot, CorporateActionSnapshot):
            raise TypeError("Expected corporate-action snapshot")
        checksum(self.source_sha256)
        now = validate_aware_datetime(self.evaluated_at, field_name="evaluated_at")
        if now.utcoffset() != timedelta(0):
            raise ValueError("Evaluation must be UTC")
        if type(self.maximum_age_days) is not int or not 1 <= self.maximum_age_days <= 365:
            raise ValueError("Invalid action age policy")
        if not self.snapshot.fetched_at <= now <= self.snapshot.fetched_at + timedelta(days=self.maximum_age_days):
            raise ValueError("Future or stale action evidence")
        dates = [e.session_date for e in self.splits]
        if len(dates) != len(set(dates)):
            raise ValueError("Ambiguous duplicate split session")

    @property
    def splits(self):
        return tuple(e for e in self.snapshot.events if e.kind == "SPLIT")

    def factor(self, timestamp: datetime, *, trade=False) -> Fraction:
        stamp = validate_aware_datetime(timestamp, field_name="timestamp")
        if not self.snapshot.start <= stamp < self.snapshot.end:
            raise ValueError("Observation outside action window")
        session = stamp.astimezone(ZoneInfo(self.snapshot.exchange_timezone)).date().isoformat()
        if trade and any(e.session_date == session for e in self.splits):
            # A daily provider label cannot certify broker intraday effective order.
            raise ValueError("Split-day trade ordering requires explicit broker evidence")
        result = Fraction(1)
        for event in self.splits:
            if event.session_date > session:
                result *= Fraction(str(event.value))
        finite_float(result)
        finite_float(1 / result)
        return result

    def to_dict(self):
        return {
            "policy": "OBSERVED_SPLITS_TO_EXCLUSIVE_END_V1",
            "snapshot_sha256": self.source_sha256,
            "snapshot_document_sha256": sha256(canonical_bytes(self.snapshot.to_dict())).hexdigest(),
            "end_exclusive": self.snapshot.end.isoformat(),
            "evaluated_at": self.evaluated_at.isoformat(),
            "maximum_age_days": self.maximum_age_days,
            "observed_split_count": len(self.splits),
            "action_completeness": "UNKNOWN",
        }


@dataclass(frozen=True, slots=True)
class SplitPriceBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        validate_aware_datetime(self.timestamp, field_name="timestamp")
        for key in ("open", "high", "low", "close"):
            value = validate_finite_number(getattr(self, key), field_name=key)
            if value <= 0:
                raise ValueError("OHLC must be positive")
            object.__setattr__(self, key, value)
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid OHLC ordering")


@dataclass(frozen=True, slots=True)
class SplitPriceSeries:
    """Caller-attested source basis. Unknown/mixed legacy storage is not eligible."""

    symbol: str
    currency: str
    basis: str
    basis_end: datetime | None
    source_sha256: str
    bars: tuple[SplitPriceBar, ...]
    split_content_sha256: str | None = None

    def __post_init__(self):
        for key in ("symbol", "currency"):
            value = getattr(self, key)
            if normalize_required_text(value, field_name=key) != value:
                raise ValueError("Price identity must be exact")
        checksum(self.source_sha256)
        if self.basis not in ("AS_TRADED", "SPLIT_ADJUSTED"):
            raise ValueError("Unknown or unsupported price basis")
        if self.basis == "AS_TRADED" and self.basis_end is not None:
            raise ValueError("As-traded series has no adjusted basis end")
        if self.basis == "AS_TRADED" and self.split_content_sha256 is not None:
            raise ValueError("As-traded series cannot already carry split adjustment")
        if self.basis == "SPLIT_ADJUSTED":
            validate_aware_datetime(self.basis_end, field_name="basis_end")
            checksum(self.split_content_sha256)
        if not isinstance(self.bars, tuple) or not 1 <= len(self.bars) <= 4000:
            raise ValueError("Expected bounded immutable price series")
        if any(not isinstance(bar, SplitPriceBar) for bar in self.bars):
            raise TypeError("Invalid price bar")
        times = tuple(bar.timestamp for bar in self.bars)
        if times != tuple(sorted(set(times))):
            raise ValueError("Price bars must be unique and ordered")


def project_split_prices(series: SplitPriceSeries, plan: SplitPlan) -> SplitPriceSeries:
    """Adjust known as-traded OHLC once; already matching basis is a no-op.

    Volumes, dividends and source stores are deliberately outside this contract.
    A hash binds supplied evidence; it does not certify its declared price basis.
    """
    if not isinstance(series, SplitPriceSeries) or not isinstance(plan, SplitPlan):
        raise TypeError("Expected typed price series and split plan")
    if (series.symbol, series.currency) != (plan.snapshot.symbol, plan.snapshot.quote_currency):
        raise ValueError("Price/action identity mismatch")
    content_hash = plan.snapshot.to_dict()["content_sha256"]
    if series.basis == "SPLIT_ADJUSTED" and (
            series.basis_end != plan.snapshot.end or series.split_content_sha256 != content_hash):
        raise ValueError("Cannot rebase an adjusted series with different split evidence")
    zone = ZoneInfo(plan.snapshot.exchange_timezone)
    dates = [bar.timestamp.astimezone(zone).date() for bar in series.bars]
    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate price session")
    bars = []
    for bar in series.bars:
        factor = plan.factor(bar.timestamp)
        if series.basis == "SPLIT_ADJUSTED":
            bars.append(bar)
        else:
            bars.append(SplitPriceBar(bar.timestamp, *(finite_float(Fraction(str(getattr(bar, key))) / factor)
                                                       for key in ("open", "high", "low", "close"))))
    return SplitPriceSeries(series.symbol, series.currency, "SPLIT_ADJUSTED",
                            plan.snapshot.end, series.source_sha256, tuple(bars), content_hash)

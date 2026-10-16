"""Candle label safety, not currency conversion or source-unit certification."""

from investment_terminal.utils.validation import normalize_required_text


class CandleUnitError(ValueError):
    """A price label cannot safely be normalized by the string-only contract."""


class UnverifiedYahooUnitError(CandleUnitError):
    """Legacy Yahoo evidence cannot distinguish the original price unit."""


def normalize_candle_currency(value: object) -> str:
    """Preserve ordinary lower-case codes, but never fold mixed-case units."""
    label = normalize_required_text(value, field_name="currency")
    if len(label) != 3 or not label.isascii() or not label.isalpha():
        raise CandleUnitError("Candle currency must be a three-letter ASCII code")
    if not (label.isupper() or label.islower()):
        raise CandleUnitError("Case-sensitive candle unit requires explicit evidence")
    return label.upper()


def require_yahoo_candle_currency(value: object) -> str:
    """Block the reproduced legacy GBp/GBP collision, including completed resume.

    No old checkpoint or manifest retains the pre-uppercase source spelling.
    Consequently even canonical GBP cannot be certified by this legacy path.
    This is a bounded compatibility gate, not a complete ISO/unit registry.
    """
    currency = normalize_candle_currency(value)
    if currency == "GBP":
        raise UnverifiedYahooUnitError(
            "Yahoo candle unit requires source evidence; preserve existing artifacts"
        )
    return currency

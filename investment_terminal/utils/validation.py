"""
Shared validation helpers for stable cross-domain primitives.
"""

from datetime import datetime
from math import isfinite
from numbers import Real


def normalize_required_text(
    value: object,
    *,
    field_name: str,
    uppercase: bool = False,
) -> str:
    """Validate and normalize a required text value."""
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    normalized = value.strip()

    if uppercase:
        normalized = normalized.upper()

    return normalized


def normalize_optional_text(
    value: object,
    *,
    field_name: str,
    uppercase: bool = False,
) -> str | None:
    """Validate and normalize an optional text value."""
    if value is None:
        return None

    return normalize_required_text(
        value,
        field_name=field_name,
        uppercase=uppercase,
    )


def validate_aware_datetime(
    value: object,
    *,
    field_name: str,
) -> datetime:
    """Validate a timezone-aware datetime and return it unchanged."""
    if not isinstance(value, datetime):
        raise TypeError(
            f"{field_name} must be a datetime"
        )

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )

    return value


def validate_finite_number(
    value: object,
    *,
    field_name: str,
) -> float:
    """Validate a finite real number and return it as float."""
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not isfinite(float(value))
    ):
        raise ValueError(
            f"{field_name} must be a finite number"
        )

    return float(value)


def validate_score_0_100(
    value: object,
    *,
    field_name: str,
) -> float:
    """Validate a finite score on the inclusive 0-100 scale."""
    normalized = validate_finite_number(
        value,
        field_name=field_name,
    )

    if not 0.0 <= normalized <= 100.0:
        raise ValueError(
            f"{field_name} must be between 0 and 100"
        )

    return normalized

"""
Tests for shared validation helpers.
"""

from datetime import datetime, timezone
from math import inf, nan

import pytest

from investment_terminal.utils.validation import (
    normalize_optional_text,
    normalize_required_text,
    validate_aware_datetime,
    validate_finite_number,
    validate_score_0_100,
)


def test_normalize_required_text_strips_value() -> None:
    assert normalize_required_text(
        "  hello  ",
        field_name="name",
    ) == "hello"


def test_normalize_required_text_can_uppercase() -> None:
    assert normalize_required_text(
        " eur ",
        field_name="currency",
        uppercase=True,
    ) == "EUR"


@pytest.mark.parametrize("value", [None, "", "   ", 123])
def test_normalize_required_text_rejects_invalid_values(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="name must be a non-empty string",
    ):
        normalize_required_text(
            value,
            field_name="name",
        )


def test_normalize_optional_text_preserves_none() -> None:
    assert normalize_optional_text(
        None,
        field_name="note",
    ) is None


def test_normalize_optional_text_normalizes_present_value() -> None:
    assert normalize_optional_text(
        "  archived  ",
        field_name="status",
        uppercase=True,
    ) == "ARCHIVED"


def test_validate_aware_datetime_accepts_aware_value() -> None:
    value = datetime(
        2026,
        8,
        5,
        17,
        0,
        tzinfo=timezone.utc,
    )

    assert validate_aware_datetime(
        value,
        field_name="generated_at",
    ) is value


def test_validate_aware_datetime_rejects_naive_value() -> None:
    with pytest.raises(
        ValueError,
        match="generated_at must be timezone-aware",
    ):
        validate_aware_datetime(
            datetime(2026, 8, 5, 17, 0),
            field_name="generated_at",
        )


def test_validate_aware_datetime_rejects_non_datetime() -> None:
    with pytest.raises(
        TypeError,
        match="generated_at must be a datetime",
    ):
        validate_aware_datetime(
            "2026-08-05T17:00:00+00:00",
            field_name="generated_at",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0.0), (12, 12.0), (12.5, 12.5)],
)
def test_validate_finite_number_accepts_real_numbers(
    value: object,
    expected: float,
) -> None:
    assert validate_finite_number(
        value,
        field_name="amount",
    ) == expected


@pytest.mark.parametrize(
    "value",
    [True, False, nan, inf, -inf, "12", None],
)
def test_validate_finite_number_rejects_invalid_values(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="amount must be a finite number",
    ):
        validate_finite_number(
            value,
            field_name="amount",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0.0), (50, 50.0), (100, 100.0)],
)
def test_validate_score_0_100_accepts_boundaries(
    value: object,
    expected: float,
) -> None:
    assert validate_score_0_100(
        value,
        field_name="score",
    ) == expected


@pytest.mark.parametrize("value", [-0.01, 100.01, 101])
def test_validate_score_0_100_rejects_out_of_range(
    value: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="score must be between 0 and 100",
    ):
        validate_score_0_100(
            value,
            field_name="score",
        )

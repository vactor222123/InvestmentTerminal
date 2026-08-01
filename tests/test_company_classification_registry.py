"""
Tests for company classification models and registry.
"""

from pathlib import Path

import pytest

from investment_terminal.market.company_classification_models import (
    CompanyClassification,
)
from investment_terminal.market.company_classification_registry import (
    CompanyClassificationRegistry,
)


def test_classification_normalizes_values() -> None:
    classification = CompanyClassification(
        symbol=" v ",
        sector=" Financial Services ",
        industry=" Credit Services ",
        business_model=" payment_network ",
    )

    assert classification.symbol == "V"
    assert classification.sector == "Financial Services"
    assert classification.industry == "Credit Services"
    assert (
        classification.business_model
        == "PAYMENT_NETWORK"
    )


def test_classification_rejects_unknown_business_model() -> None:
    with pytest.raises(
        ValueError,
        match="business_model",
    ):
        CompanyClassification(
            symbol="TEST",
            sector="Other",
            industry="Other",
            business_model="UNKNOWN",
        )


def test_registry_loads_default_dataset() -> None:
    registry = (
        CompanyClassificationRegistry.load()
    )

    assert registry.size == 30
    assert registry.source_path == Path(
        "data/company_classifications.csv"
    )


def test_registry_returns_payment_network() -> None:
    registry = (
        CompanyClassificationRegistry.load()
    )

    visa = registry.require(
        "v"
    )

    assert visa.symbol == "V"
    assert visa.business_model == (
        "PAYMENT_NETWORK"
    )


def test_registry_returns_bank() -> None:
    registry = (
        CompanyClassificationRegistry.load()
    )

    jpm = registry.require(
        "JPM"
    )

    assert jpm.business_model == "BANK"


def test_registry_returns_none_for_unknown_symbol() -> None:
    registry = (
        CompanyClassificationRegistry.load()
    )

    assert registry.get(
        "UNKNOWN"
    ) is None


def test_registry_require_rejects_unknown_symbol() -> None:
    registry = (
        CompanyClassificationRegistry.load()
    )

    with pytest.raises(
        KeyError,
        match="No company classification",
    ):
        registry.require(
            "UNKNOWN"
        )


def test_registry_reports_missing_symbols() -> None:
    registry = (
        CompanyClassificationRegistry.load()
    )

    assert registry.missing_symbols(
        (
            "MSFT",
            "UNKNOWN",
            "V",
        )
    ) == (
        "UNKNOWN",
    )


def test_registry_rejects_missing_columns(
    tmp_path,
) -> None:
    path = (
        tmp_path
        / "invalid.csv"
    )
    path.write_text(
        "symbol,sector\nMSFT,Technology\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="missing columns",
    ):
        CompanyClassificationRegistry.load(
            path
        )
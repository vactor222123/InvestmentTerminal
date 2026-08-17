"""Contract checks for the audited Phase 2 closure handoff."""

from pathlib import Path

CLOSURE = Path("docs/PHASE_2_CLOSURE.md")


def test_phase_2_closure_records_every_roadmap_scope_item() -> None:
    text = CLOSURE.read_text(encoding="utf-8")

    for scope_item in (
        "transaction ledger",
        "purchases/sales",
        "dividends",
        "fees",
        "realised/unrealised performance",
        "portfolio valuation history",
        "tax-lot readiness",
    ):
        assert scope_item in text


def test_phase_2_closure_preserves_authority_boundaries() -> None:
    text = CLOSURE.read_text(encoding="utf-8")

    assert "Canonical Review\nHistory remains immutable review evidence" in text
    assert "No jurisdiction-specific tax disposal method is inferred" in text
    assert "provider-neutral portfolio risk input contract" in text

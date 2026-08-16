from pathlib import Path


def test_sprint_33_closure_document_exists():
    assert Path(
        "docs/SPRINT_33_CLOSURE.md"
    ).exists()


def test_closure_documents_architecture_boundaries():
    text = Path(
        "docs/SPRINT_33_CLOSURE.md"
    ).read_text(
        encoding="utf-8"
    )

    assert "Analysis != AI" in text
    assert "Review Package != History" in text

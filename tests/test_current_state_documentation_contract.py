from pathlib import Path


def test_current_state_documentation_exists():
    path = Path(
        "docs/CURRENT_STATE_ANALYSIS_CLI_GUIDE.md"
    )

    assert path.exists()


def test_documentation_keeps_explicit_boundaries():
    text = Path(
        "docs/CURRENT_STATE_ANALYSIS_CLI_GUIDE.md"
    ).read_text(
        encoding="utf-8"
    )

    assert "Review Package != History" in text
    assert "Analysis != AI" in text

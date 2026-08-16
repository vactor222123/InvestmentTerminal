from pathlib import Path


def test_orchestrator_does_not_own_analysis_algorithms():
    source = Path(
        "investment_terminal/cli/current_state_analysis.py"
    ).read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "RankingEngine",
        "Recommendation",
        "Thesis",
        "AllocationEngine",
        "Yahoo",
    ):
        assert forbidden not in source

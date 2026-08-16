from investment_terminal.cli.current_state_analysis import (
    build_current_state_review_package,
)


def test_current_state_orchestrator_entry_point_exists():
    assert callable(build_current_state_review_package)

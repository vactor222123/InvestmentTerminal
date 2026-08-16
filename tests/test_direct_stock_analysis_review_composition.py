from investment_terminal.review.stock_analysis_composition import (
    build_review_package_from_current_state_analysis,
)


def test_direct_composition_entry_point_exists():
    assert callable(build_review_package_from_current_state_analysis)

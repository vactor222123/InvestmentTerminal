"""Explicit Review Package to History handoff boundary."""


def prepare_review_package_history_handoff(
    review_package,
):
    """Return review package for explicit archival handling.

    History persistence remains owned by the existing History workflow.
    This boundary intentionally does not write archives automatically.
    """
    return review_package

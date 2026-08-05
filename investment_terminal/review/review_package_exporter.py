"""
JSON exporter for the unified investment review package.
"""

from pathlib import Path

from investment_terminal.review.review_package_models import (
    InvestmentReviewPackage,
)
from investment_terminal.utils.atomic_write import (
    write_json_atomic,
)


class InvestmentReviewPackageExporter:
    """Write one review package to a UTF-8 JSON file."""

    def export(
        self,
        package: InvestmentReviewPackage,
        output_path: str | Path,
    ) -> Path:
        if not isinstance(
            package,
            InvestmentReviewPackage,
        ):
            raise TypeError(
                "package must be an InvestmentReviewPackage"
            )

        path = (
            output_path
            if isinstance(output_path, Path)
            else Path(output_path)
        )

        return write_json_atomic(
            path,
            package.to_dict(),
        )

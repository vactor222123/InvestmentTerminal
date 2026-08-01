"""
JSON exporter for the unified investment review package.
"""

import json
from pathlib import Path

from investment_terminal.review.review_package_models import (
    InvestmentReviewPackage,
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
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            json.dumps(
                package.to_dict(),
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        return path
"""
Loader for an exported portfolio-ranking analysis package.
"""

import json
from pathlib import Path
from typing import Any


class PortfolioAnalysisPackageLoader:
    """Load and validate a portfolio-ranking JSON export."""

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> dict[str, Any]:
        resolved_path = (
            path
            if isinstance(path, Path)
            else Path(path)
        )

        if not resolved_path.exists():
            raise FileNotFoundError(
                "Portfolio analysis package does not exist: "
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise ValueError(
                "Portfolio analysis package path must point to a file"
            )

        try:
            payload = json.loads(
                resolved_path.read_text(
                    encoding="utf-8",
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Portfolio analysis package contains invalid JSON"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "Portfolio analysis package root must be an object"
            )

        if not payload:
            raise ValueError(
                "Portfolio analysis package must not be empty"
            )

        return payload
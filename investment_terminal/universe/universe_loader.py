"""
Load investment universes from text files.
"""

from pathlib import Path

from investment_terminal.universe.universe_models import (
    InvestmentUniverse,
)


class UniverseLoader:
    """
    Read configurable symbol universes from plain-text files.

    Format:
    - one symbol per line;
    - empty lines are ignored;
    - lines beginning with # are comments;
    - inline comments after # are ignored;
    - comma-separated symbols are supported.
    """

    DEFAULT_DIRECTORY = Path("data") / "universes"

    def __init__(
        self,
        universe_directory: str | Path = DEFAULT_DIRECTORY,
    ) -> None:
        self.universe_directory = self._normalize_directory(
            universe_directory
        )

    def load(self, universe_name: str) -> InvestmentUniverse:
        """Load one named universe from the configured directory."""
        normalized_name = self._normalize_universe_name(
            universe_name
        )
        path = self.universe_directory / f"{normalized_name}.txt"
        return self.load_path(
            path=path,
            name=self._display_name(normalized_name),
        )

    def load_path(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> InvestmentUniverse:
        """Load one universe from an explicit text-file path."""
        resolved_path = self._normalize_path(path)

        if not resolved_path.exists():
            raise FileNotFoundError(
                f"Universe file does not exist: {resolved_path}"
            )
        if not resolved_path.is_file():
            raise ValueError("Universe path must point to a file")
        if resolved_path.suffix.lower() != ".txt":
            raise ValueError("Universe file must use the .txt extension")

        try:
            content = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Universe file must be UTF-8 encoded"
            ) from exc

        symbols = self.parse_symbols(content)
        resolved_name = (
            name
            if name is not None
            else self._display_name(resolved_path.stem)
        )

        return InvestmentUniverse(
            name=resolved_name,
            symbols=symbols,
            source_path=resolved_path,
            description=description,
        )

    @classmethod
    def parse_symbols(cls, content: str) -> tuple[str, ...]:
        """Parse, normalize, and deduplicate symbols in input order."""
        if not isinstance(content, str):
            raise TypeError("content must be a string")

        ordered_symbols: list[str] = []
        seen: set[str] = set()

        for raw_line in content.splitlines():
            line_without_comment = raw_line.split("#", maxsplit=1)[0]
            for raw_symbol in line_without_comment.split(","):
                stripped = raw_symbol.strip()
                if not stripped:
                    continue

                normalized = InvestmentUniverse._normalize_symbol(
                    stripped
                )
                if normalized in seen:
                    continue

                seen.add(normalized)
                ordered_symbols.append(normalized)

        if not ordered_symbols:
            raise ValueError(
                "Universe file does not contain any symbols"
            )

        return tuple(ordered_symbols)

    def list_available(self) -> tuple[str, ...]:
        """Return available universe file names without extensions."""
        if not self.universe_directory.exists():
            return ()

        return tuple(
            sorted(
                path.stem
                for path in self.universe_directory.glob("*.txt")
                if path.is_file()
            )
        )

    @staticmethod
    def _normalize_directory(value: str | Path) -> Path:
        if isinstance(value, Path):
            return value
        if isinstance(value, str) and value.strip():
            return Path(value.strip())
        raise ValueError(
            "universe_directory must be a non-empty path"
        )

    @staticmethod
    def _normalize_path(value: str | Path) -> Path:
        if isinstance(value, Path):
            return value
        if isinstance(value, str) and value.strip():
            return Path(value.strip())
        raise ValueError("path must be a non-empty path")

    @staticmethod
    def _normalize_universe_name(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "universe_name must be a non-empty string"
            )

        normalized = (
            value.strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_"

        if any(character not in allowed for character in normalized):
            raise ValueError(
                "universe_name may contain only letters, numbers, "
                "spaces, hyphens, and underscores"
            )

        return normalized

    @staticmethod
    def _display_name(value: str) -> str:
        return value.replace("_", " ").strip().title()
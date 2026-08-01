"""
Structured investment-universe models.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class InvestmentUniverse:
    """
    Immutable collection of unique normalized market symbols.
    """

    name: str
    symbols: tuple[str, ...]
    source_path: Path | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        normalized_name = self._normalize_name(self.name)

        if not isinstance(self.symbols, tuple):
            raise TypeError("symbols must be a tuple")
        if not self.symbols:
            raise ValueError("symbols must not be empty")

        normalized_symbols = tuple(
            self._normalize_symbol(symbol)
            for symbol in self.symbols
        )

        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("symbols must contain unique values")

        if self.source_path is not None and not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError("source_path must be a Path or None")

        normalized_description = None
        if self.description is not None:
            if not isinstance(self.description, str):
                raise TypeError("description must be a string or None")
            stripped = self.description.strip()
            if stripped:
                normalized_description = stripped

        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "symbols", normalized_symbols)
        object.__setattr__(self, "description", normalized_description)

    @property
    def size(self) -> int:
        return len(self.symbols)

    def contains(self, symbol: str) -> bool:
        """Return whether a normalized symbol belongs to the universe."""
        return self._normalize_symbol(symbol) in self.symbols

    def to_dict(self) -> dict[str, Any]:
        """Convert the universe to JSON-ready data."""
        return {
            "name": self.name,
            "size": self.size,
            "symbols": list(self.symbols),
            "source_path": (
                self.source_path.as_posix()
                if self.source_path is not None
                else None
            ),
            "description": self.description,
        }

    @staticmethod
    def _normalize_name(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("name must be a non-empty string")
        return value.strip()

    @staticmethod
    def _normalize_symbol(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("symbol must be a non-empty string")

        normalized = value.strip().upper()
        if any(character.isspace() for character in normalized):
            raise ValueError("symbol must not contain whitespace")
        return normalized
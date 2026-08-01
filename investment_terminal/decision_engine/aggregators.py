"""
Decision factor aggregation.
"""

from collections.abc import Iterable


class DecisionFactorAggregator:
    """
    Merge, normalize and deduplicate analytical factors.
    """

    @staticmethod
    def merge(
        *collections: Iterable[str],
    ) -> tuple[str, ...]:
        """
        Merge strings while preserving their original order.
        """
        result: list[str] = []
        seen: set[str] = set()

        for collection in collections:
            for value in collection:
                if (
                    not isinstance(value, str)
                    or not value.strip()
                ):
                    continue

                normalized = value.strip()
                key = normalized.casefold()

                if key in seen:
                    continue

                seen.add(key)
                result.append(normalized)

        return tuple(result)

    @staticmethod
    def build_missing_data(
        technical_missing: Iterable[str],
        fundamental_missing: Iterable[str],
    ) -> tuple[str, ...]:
        """
        Add source prefixes to unavailable fields.
        """
        technical = (
            f"technical.{field}"
            for field in technical_missing
        )
        fundamental = (
            f"fundamental.{field}"
            for field in fundamental_missing
        )

        return DecisionFactorAggregator.merge(
            technical,
            fundamental,
        )
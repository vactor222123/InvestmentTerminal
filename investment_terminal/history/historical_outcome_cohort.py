"""
Exact deterministic cohort identity for historical outcome research.
"""

from dataclasses import dataclass
from typing import Any

from investment_terminal.history.historical_methodology_aware_observation_service import (
    HistoricalMethodologyAwareObservationResult,
)
from investment_terminal.history.historical_outcome_research_protocol_models import (
    HistoricalOutcomeResearchProtocol,
)
from investment_terminal.utils.validation import (
    normalize_required_text,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeCohortDimension:
    """One ordered name/value component of a research cohort identity."""

    name: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            normalize_required_text(
                self.name,
                field_name="name",
                uppercase=True,
            ),
        )
        object.__setattr__(
            self,
            "value",
            normalize_required_text(
                self.value,
                field_name="value",
                uppercase=True,
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeCohortKey:
    """
    Stable exact research-cohort identity.

    Dimension order is protocol-defined and therefore part of the identity.
    Different methodology identity or observation-window semantics must produce
    different cohort keys.
    """

    protocol_identity: str
    dimensions: tuple[HistoricalOutcomeCohortDimension, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "protocol_identity",
            normalize_required_text(
                self.protocol_identity,
                field_name="protocol_identity",
                uppercase=True,
            ),
        )
        if not isinstance(
            self.dimensions,
            tuple,
        ):
            raise TypeError(
                "dimensions must be a tuple"
            )
        if not self.dimensions:
            raise ValueError(
                "dimensions must not be empty"
            )
        if any(
            not isinstance(
                item,
                HistoricalOutcomeCohortDimension,
            )
            for item in self.dimensions
        ):
            raise TypeError(
                "dimensions must contain only "
                "HistoricalOutcomeCohortDimension values"
            )

        names = tuple(
            item.name
            for item in self.dimensions
        )
        if len(set(names)) != len(names):
            raise ValueError(
                "cohort dimension names must be unique"
            )

    @property
    def identity_key(self) -> str:
        encoded_dimensions = "|".join(
            f"{item.name}={item.value}"
            for item in self.dimensions
        )
        return (
            f"{self.protocol_identity}"
            f"::{encoded_dimensions}"
        )

    def value_for(
        self,
        dimension_name: str,
    ) -> str | None:
        normalized = normalize_required_text(
            dimension_name,
            field_name="dimension_name",
            uppercase=True,
        )
        for item in self.dimensions:
            if item.name == normalized:
                return item.value
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_identity": self.protocol_identity,
            "identity_key": self.identity_key,
            "dimensions": [
                item.to_dict()
                for item in self.dimensions
            ],
        }


class HistoricalOutcomeCohortService:
    """Build exact cohort identities according to one research protocol."""

    def build(
        self,
        *,
        result: HistoricalMethodologyAwareObservationResult,
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> HistoricalOutcomeCohortKey:
        if not isinstance(
            result,
            HistoricalMethodologyAwareObservationResult,
        ):
            raise TypeError(
                "result must be a HistoricalMethodologyAwareObservationResult"
            )
        if not isinstance(
            protocol,
            HistoricalOutcomeResearchProtocol,
        ):
            raise TypeError(
                "protocol must be a HistoricalOutcomeResearchProtocol"
            )

        values = {
            HistoricalOutcomeResearchProtocol.METHODOLOGY_IDENTITY: (
                result.methodology.identity_key
            ),
            HistoricalOutcomeResearchProtocol.WINDOW_KIND: (
                result.observation.window.kind
            ),
            HistoricalOutcomeResearchProtocol.WINDOW_VALUE: str(
                result.observation.window.value
            ),
            HistoricalOutcomeResearchProtocol.RECOMMENDATION_KEY: (
                result.observation.recommendation_key
            ),
            HistoricalOutcomeResearchProtocol.SYMBOL: (
                result.observation.symbol
            ),
            HistoricalOutcomeResearchProtocol.ACTION: (
                result.observation.action
            ),
        }

        dimensions: list[
            HistoricalOutcomeCohortDimension
        ] = []
        for dimension_name in protocol.grouping_dimensions:
            raw_value = values[
                dimension_name
            ]
            if raw_value is None:
                raise ValueError(
                    "cannot build cohort because grouping dimension "
                    f"{dimension_name} is unavailable"
                )
            dimensions.append(
                HistoricalOutcomeCohortDimension(
                    name=dimension_name,
                    value=str(
                        raw_value
                    ),
                )
            )

        return HistoricalOutcomeCohortKey(
            protocol_identity=protocol.identity_key,
            dimensions=tuple(
                dimensions
            ),
        )

    def group(
        self,
        *,
        results: tuple[
            HistoricalMethodologyAwareObservationResult,
            ...,
        ],
        protocol: HistoricalOutcomeResearchProtocol,
    ) -> tuple[
        tuple[
            HistoricalOutcomeCohortKey,
            tuple[
                HistoricalMethodologyAwareObservationResult,
                ...,
            ],
        ],
        ...,
    ]:
        if not isinstance(
            results,
            tuple,
        ):
            raise TypeError(
                "results must be a tuple"
            )

        groups: dict[
            str,
            tuple[
                HistoricalOutcomeCohortKey,
                list[
                    HistoricalMethodologyAwareObservationResult
                ],
            ],
        ] = {}

        for result in results:
            key = self.build(
                result=result,
                protocol=protocol,
            )
            current = groups.get(
                key.identity_key
            )
            if current is None:
                groups[
                    key.identity_key
                ] = (
                    key,
                    [
                        result,
                    ],
                )
            else:
                current[
                    1
                ].append(
                    result
                )

        return tuple(
            (
                groups[
                    identity
                ][
                    0
                ],
                tuple(
                    groups[
                        identity
                    ][
                        1
                    ]
                ),
            )
            for identity in sorted(
                groups
            )
        )

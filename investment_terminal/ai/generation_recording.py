"""Recording service for durable admissible grounded generations."""

from collections.abc import Callable
from datetime import datetime

from investment_terminal.ai.audit import GroundedGenerationTrace
from investment_terminal.ai.generation_persistence_models import (
    PersistedGroundedGeneration,
)
from investment_terminal.ai.generation_persistence_projection import (
    GroundedGenerationPersistenceProjectionService,
)
from investment_terminal.ai.generation_repository import (
    GroundedGenerationRepository,
)
from investment_terminal.ai.orchestration import GroundedGenerationResult


class GroundedGenerationRecordingService:
    """
    Persist an already-admissible typed generation through the repository boundary.

    Time is supplied explicitly by an injected clock to keep recording tests
    deterministic and to keep clock ownership out of the projection model.
    """

    def __init__(
        self,
        *,
        repository: GroundedGenerationRepository,
        clock: Callable[[], datetime],
        projection_service: (
            GroundedGenerationPersistenceProjectionService | None
        ) = None,
    ) -> None:
        if not isinstance(
            repository,
            GroundedGenerationRepository,
        ):
            raise TypeError(
                "repository must be a GroundedGenerationRepository"
            )
        if not callable(clock):
            raise TypeError(
                "clock must be callable"
            )
        if (
            projection_service is not None
            and not isinstance(
                projection_service,
                GroundedGenerationPersistenceProjectionService,
            )
        ):
            raise TypeError(
                "projection_service must be a "
                "GroundedGenerationPersistenceProjectionService or None"
            )

        self._repository = repository
        self._clock = clock
        self._projection_service = (
            projection_service
            if projection_service is not None
            else GroundedGenerationPersistenceProjectionService()
        )

    def record(
        self,
        *,
        result: GroundedGenerationResult,
        trace: GroundedGenerationTrace,
        trace_data: dict,
    ) -> PersistedGroundedGeneration:
        generated_at = self._clock()
        record = self._projection_service.project(
            result=result,
            trace=trace,
            generated_at=generated_at,
            trace_data=trace_data,
        )
        return self._repository.add(
            record
        )

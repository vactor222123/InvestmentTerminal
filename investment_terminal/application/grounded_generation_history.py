"""Read-only application service for persisted grounded generations."""

from investment_terminal.ai.generation_repository import (
    GroundedGenerationRepository,
)


class GroundedGenerationHistoryService:
    """Expose bounded generated-evidence reads without persistence details."""

    def __init__(
        self,
        *,
        repository: GroundedGenerationRepository,
    ) -> None:
        if not isinstance(
            repository,
            GroundedGenerationRepository,
        ):
            raise TypeError(
                "repository must be a GroundedGenerationRepository"
            )
        self._repository = repository

    def require(
        self,
        request_id: str,
    ):
        return self._repository.require(
            request_id
        )

    def recent(
        self,
        limit: int,
    ):
        return self._repository.list_recent(
            limit
        )

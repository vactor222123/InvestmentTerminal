from datetime import datetime, timezone

import pytest

from investment_terminal.ai.context_selection import (
    GroundedContextSelectionService,
)
from investment_terminal.ai.prompt_input import (
    GroundedPromptInput,
    GroundedPromptInputService,
)
from investment_terminal.knowledge.envelope import (
    KnowledgeRecordEnvelopeService,
)
from investment_terminal.knowledge.models import (
    KnowledgeEvidenceReference,
    KnowledgeRecord,
)


def dt(day: int) -> datetime:
    return datetime(
        2026,
        8,
        day,
        12,
        0,
        tzinfo=timezone.utc,
    )


def envelope(
    knowledge_id: str,
    *,
    subject: str,
    valid_from,
    generated_at,
):
    record = KnowledgeRecord(
        knowledge_id=knowledge_id,
        knowledge_type="FACT",
        version=1,
        subject_key=subject,
        statement=f"Statement for {knowledge_id}.",
        valid_from=valid_from,
        valid_to=None,
        generated_at=generated_at,
        evidence=(
            KnowledgeEvidenceReference(
                evidence_type="HISTORICAL_SNAPSHOT",
                evidence_id=(
                    "11111111-1111-4111-8111-"
                    + f"{len(knowledge_id):012d}"
                ),
                observed_at=valid_from,
                checksum_sha256="a" * 64,
            ),
        ),
    )
    return KnowledgeRecordEnvelopeService().build(
        record
    )


def selection():
    first = envelope(
        "WORLD_A",
        subject="WORLD",
        valid_from=dt(1),
        generated_at=dt(2),
    )
    second = envelope(
        "EM_A",
        subject="EM",
        valid_from=dt(1),
        generated_at=dt(2),
    )
    return GroundedContextSelectionService().select(
        (
            first,
            second,
        )
    )


def test_build_preserves_selected_context_order() -> None:
    selected = selection()

    prompt = GroundedPromptInputService().build(
        request_id="request-1",
        user_query="What historical context is available?",
        selection=selected,
    )

    assert prompt.context_identities == (
        "EM_A@1",
        "WORLD_A@1",
    )
    assert prompt.context_identities == (
        selected.selected_identities
    )


def test_context_item_preserves_exact_statement_and_provenance() -> None:
    selected = selection()

    prompt = GroundedPromptInputService().build(
        request_id="request-1",
        user_query="Question",
        selection=selected,
    )

    item = prompt.context[0]
    source = selected.selected[0]

    assert item.knowledge_identity == source.identity_key
    assert item.subject_key == source.record.subject_key
    assert item.statement == source.record.statement
    assert item.provenance_status == source.provenance.status
    assert item.valid_from == source.record.valid_from.isoformat()
    assert item.valid_to is None


def test_prompt_uses_versioned_protocol_identity() -> None:
    prompt = GroundedPromptInputService().build(
        request_id="request-1",
        user_query="Question",
        selection=selection(),
    )

    assert prompt.protocol_identity == (
        "EVIDENCE_GROUNDED_PROMPT@1"
    )


def test_empty_selected_context_is_allowed_and_explicit() -> None:
    selected = GroundedContextSelectionService().select(
        ()
    )

    prompt = GroundedPromptInputService().build(
        request_id="request-empty",
        user_query="Question",
        selection=selected,
    )

    assert prompt.context == ()
    assert prompt.context_identities == ()


def test_serialization_is_provider_neutral_and_stable() -> None:
    prompt = GroundedPromptInputService().build(
        request_id="request-1",
        user_query="Question",
        selection=selection(),
    )

    data = prompt.to_dict()

    assert data["request_id"] == "request-1"
    assert data["protocol_identity"] == (
        "EVIDENCE_GROUNDED_PROMPT@1"
    )
    assert data["context_identities"] == [
        "EM_A@1",
        "WORLD_A@1",
    ]


def test_unknown_protocol_identity_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="EVIDENCE_GROUNDED_PROMPT@1",
    ):
        GroundedPromptInput(
            request_id="request-1",
            protocol_identity="PROVIDER_PROMPT@1",
            user_query="Question",
            context=(),
        )


def test_service_rejects_wrong_selection_type() -> None:
    with pytest.raises(
        TypeError,
        match="selection must be",
    ):
        GroundedPromptInputService().build(
            request_id="request-1",
            user_query="Question",
            selection=object(),  # type: ignore[arg-type]
        )


def test_prompt_contract_contains_no_provider_or_generation_controls() -> None:
    serialized = str(
        GroundedPromptInputService().build(
            request_id="request-1",
            user_query="Question",
            selection=selection(),
        ).to_dict()
    ).lower()

    for key in (
        "openai",
        "anthropic",
        "model",
        "temperature",
        "top_p",
        "max_tokens",
        "api_key",
        "endpoint",
        "embedding",
        "relevance_score",
    ):
        assert key not in serialized

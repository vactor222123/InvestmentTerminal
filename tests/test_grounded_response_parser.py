import json

import pytest

from investment_terminal.ai.model_adapter import (
    GroundedModelResponse,
)
from investment_terminal.ai.response_parser import (
    GroundedModelResponseParser,
)


def payload():
    return {
        "answer_id": "answer-1",
        "protocol_identity": "EVIDENCE_GROUNDED_ANSWER@1",
        "claims": [
            {
                "text": "Historical context is available.",
                "citations": [
                    {
                        "knowledge_identity": "WORLD_CONTEXT@1",
                        "statement": "WORLD was present historically.",
                        "provenance_status": "COMPLETE",
                    }
                ],
            }
        ],
    }


def response(data=None):
    raw = (
        payload()
        if data is None
        else data
    )
    return GroundedModelResponse(
        request_id="request-1",
        provider_identity="TEST_PROVIDER",
        model_identity="TEST_MODEL@1",
        raw_text=json.dumps(
            raw
        ),
    )


def test_parser_builds_candidate_answer_and_preserves_correlation() -> None:
    result = GroundedModelResponseParser().parse(
        response()
    )

    assert result.request_id == "request-1"
    assert result.provider_identity == "TEST_PROVIDER"
    assert result.model_identity == "TEST_MODEL@1"
    assert result.answer.answer_id == "answer-1"
    assert result.answer.claims[0].text == (
        "Historical context is available."
    )
    assert result.answer.claims[0].citations[0].knowledge_identity == (
        "WORLD_CONTEXT@1"
    )


def test_parse_result_serializes_candidate_answer() -> None:
    data = GroundedModelResponseParser().parse(
        response()
    ).to_dict()

    assert data["request_id"] == "request-1"
    assert data["answer"]["protocol_identity"] == (
        "EVIDENCE_GROUNDED_ANSWER@1"
    )


def test_invalid_json_is_rejected() -> None:
    bad = GroundedModelResponse(
        request_id="request-1",
        provider_identity="TEST_PROVIDER",
        model_identity="TEST_MODEL@1",
        raw_text="{not-json",
    )

    with pytest.raises(
        ValueError,
        match="valid JSON",
    ):
        GroundedModelResponseParser().parse(
            bad
        )


def test_non_object_json_is_rejected() -> None:
    bad = GroundedModelResponse(
        request_id="request-1",
        provider_identity="TEST_PROVIDER",
        model_identity="TEST_MODEL@1",
        raw_text='["not", "an", "object"]',
    )

    with pytest.raises(
        ValueError,
        match="must be an object",
    ):
        GroundedModelResponseParser().parse(
            bad
        )


def test_missing_top_level_field_is_rejected() -> None:
    data = payload()
    del data[
        "claims"
    ]

    with pytest.raises(
        ValueError,
        match="missing required fields: claims",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_extra_top_level_field_is_rejected() -> None:
    data = payload()
    data[
        "confidence"
    ] = 0.99

    with pytest.raises(
        ValueError,
        match="unsupported fields: confidence",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_claim_requires_exact_fields() -> None:
    data = payload()
    data["claims"][0][
        "extra"
    ] = "not allowed"

    with pytest.raises(
        ValueError,
        match="claims\\[0\\] contains unsupported fields: extra",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_citation_requires_exact_fields() -> None:
    data = payload()
    del data["claims"][0]["citations"][0][
        "statement"
    ]

    with pytest.raises(
        ValueError,
        match="missing required fields: statement",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_empty_claim_list_fails_through_answer_contract() -> None:
    data = payload()
    data[
        "claims"
    ] = []

    with pytest.raises(
        ValueError,
        match="at least one claim",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_empty_citations_fail_through_claim_contract() -> None:
    data = payload()
    data["claims"][0][
        "citations"
    ] = []

    with pytest.raises(
        ValueError,
        match="at least one citation",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_unknown_protocol_fails_through_answer_contract() -> None:
    data = payload()
    data[
        "protocol_identity"
    ] = "OTHER@1"

    with pytest.raises(
        ValueError,
        match="EVIDENCE_GROUNDED_ANSWER@1",
    ):
        GroundedModelResponseParser().parse(
            response(
                data
            )
        )


def test_parser_does_not_assert_grounding_admissibility() -> None:
    data = payload()
    data["claims"][0]["citations"][0][
        "knowledge_identity"
    ] = "DOES_NOT_EXIST@1"

    result = GroundedModelResponseParser().parse(
        response(
            data
        )
    )

    assert result.answer.claims[0].citations[0].knowledge_identity == (
        "DOES_NOT_EXIST@1"
    )


def test_parser_rejects_wrong_response_type() -> None:
    with pytest.raises(
        TypeError,
        match="GroundedModelResponse",
    ):
        GroundedModelResponseParser().parse(
            object()  # type: ignore[arg-type]
        )

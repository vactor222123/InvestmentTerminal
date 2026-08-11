from investment_terminal.application.grounded_ai import (
    GroundedAIApplicationRequest,
)
from investment_terminal.application.live_grounded_ai import (
    LiveGroundedAIApplicationService,
)
from investment_terminal.cli import grounded_ai_live


def test_run_live_delegates_to_application_service(
    monkeypatch,
) -> None:
    calls = {}

    class FakeApplicationService:
        def __init__(self, **kwargs):
            calls["init"] = kwargs

        def execute(self, request):
            calls["request"] = request

            class Result:
                def to_dict(self):
                    return {
                        "generation": {
                            "prompt": {
                                "request_id": request.request_id,
                            }
                        },
                        "trace": {
                            "request_id": request.request_id,
                        },
                    }

            return Result()

    monkeypatch.setattr(
        grounded_ai_live,
        "LiveGroundedAIApplicationService",
        FakeApplicationService,
    )

    class Query:
        pass

    class GenerationService:
        pass

    report = grounded_ai_live._run_live(
        query=Query(),
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable="UNUSED",
        timeout_seconds=10,
        max_retries=0,
        subjects=("WORLD",),
        max_items=3,
        generation_service=GenerationService(),
    )

    assert isinstance(
        calls["request"],
        GroundedAIApplicationRequest,
    )
    assert calls["request"].request_id == "request-1"
    assert calls["request"].user_query == "Question"
    assert calls["request"].subject_keys == ("WORLD",)
    assert calls["request"].max_items == 3

    assert set(report) == {
        "generation",
        "trace",
    }


def test_run_live_passes_existing_policies_to_application_service(
    monkeypatch,
) -> None:
    calls = {}

    class FakeApplicationService:
        def __init__(self, **kwargs):
            calls.update(kwargs)

        def execute(self, request):
            class Result:
                def to_dict(self):
                    return {
                        "generation": {
                            "prompt": {
                                "request_id": request.request_id,
                            }
                        },
                        "trace": {
                            "request_id": request.request_id,
                        },
                    }

            return Result()

    monkeypatch.setattr(
        grounded_ai_live,
        "LiveGroundedAIApplicationService",
        FakeApplicationService,
    )

    pricing = object()
    budget = object()
    generation = object()
    query = object()

    grounded_ai_live._run_live(
        query=query,  # type: ignore[arg-type]
        request_id="request-1",
        user_query="Question",
        model_identity="gpt-test",
        api_key_environment_variable="UNUSED",
        timeout_seconds=10,
        max_retries=0,
        subjects=(),
        max_items=None,
        pricing_policy=pricing,  # type: ignore[arg-type]
        budget_policy=budget,  # type: ignore[arg-type]
        requested_max_output_tokens=123,
        generation_service=generation,
    )

    assert calls["query"] is query
    assert calls["generation_service"] is generation
    assert calls["pricing_policy"] is pricing
    assert calls["budget_policy"] is budget
    assert calls["requested_max_output_tokens"] == 123

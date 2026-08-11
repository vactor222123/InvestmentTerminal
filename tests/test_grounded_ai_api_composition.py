from pathlib import Path

from investment_terminal.api import composition


def test_api_composition_delegates_application_construction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = {}

    class FakeApplication:
        pass

    class FakeHandler:
        def __init__(self, *, application_service):
            calls["application_service"] = application_service

    def fake_build_application(**kwargs):
        calls["application_kwargs"] = kwargs
        return FakeApplication()

    monkeypatch.setattr(
        composition,
        "build_live_grounded_ai_application",
        fake_build_application,
    )
    monkeypatch.setattr(
        composition,
        "GroundedAIHTTPHandler",
        FakeHandler,
    )

    database = tmp_path / "knowledge.db"
    governance = object()

    result = composition.build_live_grounded_ai_http_handler(
        database=database,
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=2,
        governance_policy=governance,  # type: ignore[arg-type]
        requested_max_output_tokens=123,
    )

    assert isinstance(
        result,
        FakeHandler,
    )
    assert isinstance(
        calls["application_service"],
        FakeApplication,
    )

    assert calls["application_kwargs"]["database"] == database
    assert calls["application_kwargs"]["model_identity"] == "gpt-test"
    assert calls["application_kwargs"]["timeout_seconds"] == 10
    assert calls["application_kwargs"]["max_retries"] == 2
    assert (
        calls["application_kwargs"]["governance_policy"]
        is governance
    )
    assert (
        calls["application_kwargs"]["requested_max_output_tokens"]
        == 123
    )


def test_api_composition_does_not_construct_provider_or_database_directly(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls = {
        "application_builds": 0,
    }

    class FakeApplication:
        pass

    class FakeHandler:
        def __init__(self, *, application_service):
            assert isinstance(
                application_service,
                FakeApplication,
            )

    def fake_build_application(**kwargs):
        calls["application_builds"] += 1
        return FakeApplication()

    monkeypatch.setattr(
        composition,
        "build_live_grounded_ai_application",
        fake_build_application,
    )
    monkeypatch.setattr(
        composition,
        "GroundedAIHTTPHandler",
        FakeHandler,
    )

    composition.build_live_grounded_ai_http_handler(
        database=tmp_path / "knowledge.db",
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=0,
        governance_policy=object(),  # type: ignore[arg-type]
    )

    assert calls["application_builds"] == 1


def test_api_composition_forwards_retry_pricing_and_budget_controls(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls = {}

    class FakeHandler:
        def __init__(self, *, application_service):
            pass

    def fake_build_application(**kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr(
        composition,
        "build_live_grounded_ai_application",
        fake_build_application,
    )
    monkeypatch.setattr(
        composition,
        "GroundedAIHTTPHandler",
        FakeHandler,
    )

    pricing = object()
    budget = object()

    composition.build_live_grounded_ai_http_handler(
        database=tmp_path / "knowledge.db",
        model_identity="gpt-test",
        timeout_seconds=10,
        max_retries=2,
        governance_policy=object(),  # type: ignore[arg-type]
        retry_initial_delay_seconds=1,  # type: ignore[arg-type]
        retry_delay_multiplier=2,  # type: ignore[arg-type]
        retry_maximum_delay_seconds=4,  # type: ignore[arg-type]
        pricing_policy=pricing,  # type: ignore[arg-type]
        budget_policy=budget,  # type: ignore[arg-type]
    )

    assert calls["retry_initial_delay_seconds"] == 1
    assert calls["retry_delay_multiplier"] == 2
    assert calls["retry_maximum_delay_seconds"] == 4
    assert calls["pricing_policy"] is pricing
    assert calls["budget_policy"] is budget

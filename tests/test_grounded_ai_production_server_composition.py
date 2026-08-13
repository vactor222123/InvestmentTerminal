from investment_terminal.server import production
from investment_terminal.server.rate_limit_admission import (
    GroundedAIServerRateLimitAdmissionService,
)
from investment_terminal.server.rate_limit_identity import (
    GroundedAIServerRateLimitIdentityDeriver,
)
from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    DEFAULT_SERVER_API_KEY_ENV,
    MODEL_ENV,
)


def test_production_factory_routes_config_through_api_composition(monkeypatch):
    calls = {}

    class FakeHandler:
        pass

    class FakeApp:
        pass

    def fake_build_handler(**kwargs):
        calls["handler_kwargs"] = kwargs
        return FakeHandler()

    def fake_fastapi_factory(
        *,
        handler,
        readiness_service,
        authenticator,
        request_limit_policy,
        rate_limit_admission_service,
        rate_limit_identity_deriver,
    ):
        calls["handler"] = handler
        calls["readiness_service"] = readiness_service
        calls["authenticator"] = authenticator
        calls["request_limit_policy"] = request_limit_policy
        calls["rate_limit_admission_service"] = rate_limit_admission_service
        calls["rate_limit_identity_deriver"] = rate_limit_identity_deriver
        return FakeApp()

    monkeypatch.setattr(production, "build_live_grounded_ai_http_handler", fake_build_handler)
    monkeypatch.setattr(production, "create_grounded_ai_fastapi_app", fake_fastapi_factory)

    app = production.create_app({
        DATABASE_ENV: "data/knowledge/knowledge.db",
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        DEFAULT_SERVER_API_KEY_ENV: "server-secret",
    })

    assert isinstance(app, FakeApp)
    assert isinstance(calls["handler"], FakeHandler)
    assert calls["readiness_service"] is not None
    assert calls["authenticator"].authenticate("server-secret")
    assert calls["request_limit_policy"].max_body_bytes == 65536
    assert isinstance(
        calls["rate_limit_admission_service"],
        GroundedAIServerRateLimitAdmissionService,
    )
    assert isinstance(
        calls["rate_limit_identity_deriver"],
        GroundedAIServerRateLimitIdentityDeriver,
    )
    assert calls["handler_kwargs"]["model_identity"] == "gpt-test"
    assert calls["handler_kwargs"]["timeout_seconds"] == 30
    assert calls["handler_kwargs"]["max_retries"] == 2
    assert calls["handler_kwargs"]["governance_policy"].assess(
        provider_identity="OPENAI",
        model_identity="gpt-test",
    ).allowed


def test_production_module_has_no_import_time_app_construction():
    assert not hasattr(production, "app")

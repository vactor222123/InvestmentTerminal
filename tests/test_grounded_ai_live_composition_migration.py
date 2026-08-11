from investment_terminal.cli import grounded_ai_live


def test_main_uses_application_composition_root(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    calls = {}

    class FakeResult:
        def to_dict(self):
            return {
                "generation": {
                    "answer": {
                        "claims": [],
                    }
                },
                "trace": {
                    "request_id": "request-1",
                    "provider_identity": "OPENAI",
                    "model_identity": "gpt-test",
                    "validation_status": "ADMISSIBLE",
                    "selected_knowledge_identities": [],
                    "claim_count": 0,
                    "citation_count": 0,
                },
            }

    class FakeApplication:
        def execute(self, request):
            calls["request"] = request
            return FakeResult()

    def fake_build(**kwargs):
        calls["composition"] = kwargs
        return FakeApplication()

    monkeypatch.setattr(
        grounded_ai_live,
        "build_live_grounded_ai_application",
        fake_build,
    )

    grounded_ai_live.main(
        [
            "--live",
            "--database",
            str(tmp_path / "knowledge.db"),
            "--request-id",
            "request-1",
            "--query",
            "Question",
            "--model",
            "gpt-test",
            "--allow-model",
            "gpt-test",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert '"request_id": "request-1"' in output

    assert (
        calls["composition"]["database"]
        == tmp_path / "knowledge.db"
    )
    assert (
        calls["composition"]["model_identity"]
        == "gpt-test"
    )
    assert (
        calls["request"].request_id
        == "request-1"
    )
    assert calls["request"].user_query == "Question"


def test_main_does_not_require_cli_level_database_constructor(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeResult:
        def to_dict(self):
            return {
                "generation": {
                    "answer": {
                        "claims": [],
                    }
                },
                "trace": {
                    "request_id": "r",
                    "provider_identity": "OPENAI",
                    "model_identity": "gpt-test",
                    "validation_status": "ADMISSIBLE",
                    "selected_knowledge_identities": [],
                    "claim_count": 0,
                    "citation_count": 0,
                },
            }

    class FakeApplication:
        def execute(self, request):
            return FakeResult()

    monkeypatch.setattr(
        grounded_ai_live,
        "build_live_grounded_ai_application",
        lambda **kwargs: FakeApplication(),
    )

    grounded_ai_live.main(
        [
            "--live",
            "--database",
            str(tmp_path / "not-created-here.db"),
            "--request-id",
            "r",
            "--query",
            "Q",
            "--model",
            "gpt-test",
            "--allow-model",
            "gpt-test",
            "--json",
        ]
    )

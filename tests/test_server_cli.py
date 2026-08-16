import pytest

from investment_terminal.cli import server as server_cli


def test_server_cli_uses_production_factory_target(
    monkeypatch,
) -> None:
    calls = {}

    def fake_run(app, **kwargs):
        calls["app"] = app
        calls["kwargs"] = kwargs

    monkeypatch.setattr(
        server_cli.uvicorn,
        "run",
        fake_run,
    )

    result = server_cli.main(
        [
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--workers",
            "1",
            "--log-level",
            "warning",
        ]
    )

    assert result == 0
    assert calls["app"] == (
        "investment_terminal.server.production:create_app"
    )
    assert calls["kwargs"] == {
        "factory": True,
        "host": "0.0.0.0",
        "port": 9000,
        "workers": 1,
        "log_level": "warning",
        "proxy_headers": False,
    }


def test_server_cli_defaults_are_conservative(
    monkeypatch,
) -> None:
    calls = {}

    monkeypatch.setattr(
        server_cli.uvicorn,
        "run",
        lambda app, **kwargs: calls.update(
            {
                "app": app,
                **kwargs,
            }
        ),
    )

    server_cli.main(
        []
    )

    assert calls["host"] == "127.0.0.1"
    assert calls["port"] == 8000
    assert calls["workers"] == 1
    assert calls["factory"] is True
    assert calls["proxy_headers"] is False


@pytest.mark.parametrize(
    "argv",
    [
        ["--port", "0"],
        ["--port", "65536"],
        ["--workers", "0"],
        ["--workers", "-1"],
        ["--workers", "2"],
        ["--host", "   "],
    ],
)
def test_server_cli_rejects_invalid_runtime_arguments(
    argv,
) -> None:
    with pytest.raises(
        SystemExit,
    ):
        server_cli.main(
            argv
        )


def test_server_module_does_not_import_production_factory_directly() -> None:
    namespace = vars(
        server_cli
    )

    assert "create_app" not in namespace

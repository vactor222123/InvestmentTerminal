from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"


def dockerfile() -> str:
    return DOCKERFILE.read_text(
        encoding="utf-8"
    )


def dockerignore() -> str:
    return DOCKERIGNORE.read_text(
        encoding="utf-8"
    )


def test_container_uses_python_313_runtime_family() -> None:
    content = dockerfile()

    assert content.startswith(
        "FROM python:3.13-slim"
    )


def test_container_installs_hash_locked_runtime_dependencies() -> None:
    content = dockerfile()

    assert "COPY requirements.lock" in content
    assert (
        "python -m pip install --no-cache-dir --require-hashes"
        in content
    )
    assert "requirements-dev.lock" not in content


def test_container_runs_as_non_root_user() -> None:
    content = dockerfile()

    assert (
        "USER investment-terminal:investment-terminal"
        in content
    )
    assert "USER root" not in content


def test_container_consumes_canonical_runtime_layout() -> None:
    content = dockerfile()

    assert (
        "INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT=/runtime"
        in content
    )
    assert (
        "INVESTMENT_TERMINAL_KNOWLEDGE_DATABASE=/runtime/knowledge.db"
        in content
    )
    assert (
        "INVESTMENT_TERMINAL_PROVIDER_USAGE_COST_DATABASE="
        "/runtime/operational/provider_usage_cost.db"
        in content
    )
    assert (
        "INVESTMENT_TERMINAL_GROUNDED_GENERATION_DATABASE="
        "/runtime/operational/grounded_generations.db"
        in content
    )
    assert 'VOLUME ["/runtime", "/backups"]' in content


def test_application_tree_is_made_read_only() -> None:
    content = dockerfile()

    assert "PYTHONDONTWRITEBYTECODE=1" in content
    assert "RUN chmod -R a-w /application" in content


def test_healthcheck_uses_liveness_endpoint_not_readiness() -> None:
    content = dockerfile()

    healthcheck = next(
        line
        for line in content.splitlines()
        if line.startswith("HEALTHCHECK ")
    )
    assert "/health" in content
    assert "/ready" not in healthcheck


def test_container_runs_canonical_single_worker_server_cli() -> None:
    content = dockerfile()

    assert (
        'CMD ["python", "-m", "investment_terminal.cli.server", '
        '"--host", "0.0.0.0", "--port", "8000", "--workers", "1"]'
        in content
    )


def test_build_context_excludes_local_runtime_and_secret_material() -> None:
    content = dockerignore()

    for required in (
        ".env",
        "data",
        "backups",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "*-wal",
        "*-shm",
    ):
        assert required in content


def test_build_context_excludes_development_only_payload() -> None:
    content = dockerignore()

    assert "tests" in content
    assert "requirements-dev.lock" in content
    assert "requirements-dev.in" in content

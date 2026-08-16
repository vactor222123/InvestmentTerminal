from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "ci.yml"
)


def workflow() -> str:
    return WORKFLOW.read_text(
        encoding="utf-8"
    )


def test_ci_preserves_python_regression_job() -> None:
    content = workflow()

    assert "Python 3.13 / tests" in content
    assert "python -m pytest -q" in content
    assert "git diff --check" in content


def test_ci_builds_real_production_image() -> None:
    content = workflow()

    assert "container-smoke:" in content
    assert "docker build --tag investment-terminal:ci ." in content


def test_ci_starts_container_with_isolated_runtime_mount() -> None:
    content = workflow()

    assert "--name investment-terminal-ci" in content
    assert (
        "${RUNNER_TEMP}/investment-terminal-runtime:/runtime"
        in content
    )
    assert "touch " in content
    assert "knowledge.db" in content


def test_ci_uses_only_synthetic_smoke_secrets() -> None:
    content = workflow()

    assert "provider-smoke-secret" in content
    assert "server-smoke-secret" in content
    assert "${{ secrets." not in content


def test_ci_verifies_liveness_and_readiness_separately() -> None:
    content = workflow()

    assert "Wait for liveness" in content
    assert "http://127.0.0.1:8000/health" in content
    assert "Verify readiness" in content
    assert "http://127.0.0.1:8000/ready" in content
    assert '"status": "READY"' in content


def test_ci_verifies_non_root_runtime_identity() -> None:
    content = workflow()

    assert "docker exec investment-terminal-ci id -u" in content
    assert '!= "0"' in content


def test_ci_does_not_call_grounded_ai_provider_route() -> None:
    content = workflow()

    assert "/v1/grounded-ai" not in content


def test_ci_captures_logs_and_always_cleans_up() -> None:
    content = workflow()

    assert "Capture container logs on failure" in content
    assert "if: failure()" in content
    assert "docker logs investment-terminal-ci" in content
    assert "Clean up container" in content
    assert "if: always()" in content
    assert "docker rm --force investment-terminal-ci" in content

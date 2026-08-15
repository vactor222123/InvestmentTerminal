from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (
    PROJECT_ROOT
    / ".github"
    / "workflows"
    / "ci.yml"
)


def _workflow_text() -> str:
    return WORKFLOW.read_text(
        encoding="utf-8"
    )


def test_ci_workflow_exists() -> None:
    assert WORKFLOW.is_file()


def test_ci_targets_develop_push_and_pull_request() -> None:
    text = _workflow_text()

    assert "push:" in text
    assert "pull_request:" in text
    assert text.count("- develop") == 2


def test_ci_uses_python_313_and_locked_dependencies() -> None:
    text = _workflow_text()

    assert 'python-version: "3.13"' in text
    assert "requirements-dev.lock" in text
    assert (
        "python -m pip install --require-hashes "
        "-r requirements-dev.lock"
    ) in text


def test_ci_runs_reproducibility_and_architecture_contracts() -> None:
    text = _workflow_text()

    assert (
        "python -m pytest "
        "tests/test_dependency_reproducibility_contract.py -q"
    ) in text
    assert (
        "python -m pytest "
        "tests/test_architecture_dependencies.py -q"
    ) in text


def test_ci_runs_full_pytest_suite() -> None:
    text = _workflow_text()

    assert "python -m pytest -q" in text


def test_ci_checks_whitespace_errors() -> None:
    text = _workflow_text()

    assert "git diff --check" in text


def test_ci_does_not_require_secrets_or_network_provider_calls() -> None:
    text = _workflow_text().lower()

    assert "secrets." not in text
    assert "openai_api_key" not in text
    assert "finnhub_api_key" not in text


def test_ci_has_read_only_repository_permissions() -> None:
    text = _workflow_text()

    assert "permissions:" in text
    assert "contents: read" in text

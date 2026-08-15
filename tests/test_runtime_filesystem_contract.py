from pathlib import Path

import pytest

from investment_terminal.server.runtime_config import (
    ALLOWED_MODELS_ENV,
    DATABASE_ENV,
    GROUNDED_GENERATION_DATABASE_ENV,
    MODEL_ENV,
    PROVIDER_BUDGET_CURRENCY_ENV,
    PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_MAX_OUTPUT_TOKENS_ENV,
    PROVIDER_MAX_TOTAL_COST_ENV,
    PROVIDER_MAX_TOTAL_TOKENS_ENV,
    PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV,
    PROVIDER_PRICING_CURRENCY_ENV,
    RUNTIME_DATA_ROOT_ENV,
    USAGE_COST_LEDGER_DATABASE_ENV,
    GroundedAIServerRuntimeConfig,
)
from investment_terminal.server.runtime_filesystem import (
    GroundedAIServerRuntimeFilesystemContract,
)


def environment(
    *,
    root: Path,
) -> dict[str, str]:
    return {
        RUNTIME_DATA_ROOT_ENV: str(root),
        DATABASE_ENV: str(
            root / "knowledge.db"
        ),
        USAGE_COST_LEDGER_DATABASE_ENV: str(
            root / "operational" / "provider_usage_cost.db"
        ),
        GROUNDED_GENERATION_DATABASE_ENV: str(
            root / "operational" / "grounded_generations.db"
        ),
        MODEL_ENV: "gpt-test",
        ALLOWED_MODELS_ENV: "gpt-test",
        PROVIDER_MAX_OUTPUT_TOKENS_ENV: "32",
        PROVIDER_MAX_TOTAL_TOKENS_ENV: "128",
        PROVIDER_MAX_TOTAL_COST_ENV: "1.50",
        PROVIDER_BUDGET_CURRENCY_ENV: "EUR",
        PROVIDER_INPUT_COST_PER_MILLION_TOKENS_ENV: "0.10",
        PROVIDER_OUTPUT_COST_PER_MILLION_TOKENS_ENV: "0.20",
        PROVIDER_PRICING_CURRENCY_ENV: "EUR",
    }


def contract(
    *,
    root: Path,
) -> GroundedAIServerRuntimeFilesystemContract:
    config = GroundedAIServerRuntimeConfig.from_environment(
        environment(
            root=root
        )
    )
    return GroundedAIServerRuntimeFilesystemContract.from_config(
        config
    )


def test_unconfigured_runtime_root_preserves_legacy_behavior(
    tmp_path: Path,
) -> None:
    values = environment(
        root=tmp_path / "runtime"
    )
    del values[
        RUNTIME_DATA_ROOT_ENV
    ]

    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    result = GroundedAIServerRuntimeFilesystemContract.from_config(
        config
    ).prepare()

    assert result is None


def test_prepare_creates_root_and_writable_operational_parents(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    expected_operational = (
        root / "operational"
    )

    prepared = contract(
        root=root
    ).prepare()

    assert prepared == root.resolve()
    assert root.is_dir()
    assert expected_operational.is_dir()


def test_prepare_does_not_create_missing_knowledge_database(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"

    contract(
        root=root
    ).prepare()

    assert not (
        root / "knowledge.db"
    ).exists()


def test_database_escape_from_runtime_root_fails_closed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    values = environment(
        root=root
    )
    values[
        GROUNDED_GENERATION_DATABASE_ENV
    ] = str(
        tmp_path
        / "outside"
        / "grounded_generations.db"
    )
    config = GroundedAIServerRuntimeConfig.from_environment(
        values
    )

    with pytest.raises(
        ValueError,
        match="grounded_generation_database.*inside runtime data root",
    ):
        GroundedAIServerRuntimeFilesystemContract.from_config(
            config
        ).prepare()


def test_runtime_root_cannot_be_an_existing_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    root.write_text(
        "not-a-directory",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="runtime data root must be a directory",
    ):
        contract(
            root=root
        ).prepare()


def test_existing_knowledge_path_must_be_a_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    knowledge = root / "knowledge.db"
    knowledge.mkdir(
        parents=True
    )

    with pytest.raises(
        ValueError,
        match="knowledge_database must resolve to a file",
    ):
        contract(
            root=root
        ).prepare()


def test_existing_symlink_parent_cannot_escape_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    outside = tmp_path / "outside"
    outside.mkdir()
    root.mkdir()

    link = root / "operational"
    try:
        link.symlink_to(
            outside,
            target_is_directory=True,
        )
    except (
        OSError,
        NotImplementedError,
    ):
        pytest.skip(
            "directory symlinks are unavailable on this platform"
        )

    with pytest.raises(
        ValueError,
        match="provider_usage_cost_database.*inside runtime data root",
    ):
        contract(
            root=root
        ).prepare()

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from investment_terminal.ai.generation_sqlite_store import (
    GroundedGenerationSQLiteStore,
)
from investment_terminal.ai.providers.usage_ledger_sqlite_store import (
    GroundedProviderUsageCostLedgerSQLiteStore,
)
from investment_terminal.knowledge.sqlite_store import (
    KnowledgeSQLiteStore,
)
from investment_terminal.persistence.runtime_backup_service import (
    RuntimeSQLiteBackupService,
    RuntimeSQLiteBackupSources,
)
from investment_terminal.persistence.runtime_restore_activation import (
    RuntimeSQLiteRestoreTargets,
    activate_runtime_sqlite_restore,
)
from investment_terminal.persistence.runtime_restore_validation import (
    validate_runtime_sqlite_restore_candidate,
)


BACKUP_TIME = datetime(
    2026,
    8,
    16,
    12,
    30,
    tzinfo=timezone.utc,
)


def test_real_runtime_backup_restore_recovers_exact_pre_backup_state(
    tmp_path: Path,
) -> None:
    live = tmp_path / "live"
    knowledge_path = live / "knowledge.db"
    ledger_path = live / "provider_usage_cost.db"
    generations_path = live / "grounded_generations.db"

    knowledge_store = KnowledgeSQLiteStore(
        knowledge_path
    )
    ledger_store = GroundedProviderUsageCostLedgerSQLiteStore(
        ledger_path
    )
    generation_store = GroundedGenerationSQLiteStore(
        generations_path
    )

    knowledge_store.initialize()
    ledger_store.initialize()
    generation_store.initialize()

    _write_pre_backup_state(
        knowledge_store=knowledge_store,
        ledger_store=ledger_store,
        generation_store=generation_store,
    )

    expected = _read_all_state(
        knowledge_store=knowledge_store,
        ledger_store=ledger_store,
        generation_store=generation_store,
    )

    backup = RuntimeSQLiteBackupService(
        backup_root=tmp_path / "backups",
        sources=RuntimeSQLiteBackupSources(
            knowledge_database=knowledge_path,
            usage_cost_ledger_database=ledger_path,
            grounded_generation_database=generations_path,
        ),
        clock=lambda: BACKUP_TIME,
    ).create_backup_set()

    candidate = validate_runtime_sqlite_restore_candidate(
        backup.directory
    )
    assert candidate.backup_set_id == backup.backup_set_id
    assert len(candidate.databases) == 3

    _write_post_backup_mutations(
        knowledge_store=knowledge_store,
        ledger_store=ledger_store,
        generation_store=generation_store,
    )

    mutated = _read_all_state(
        knowledge_store=knowledge_store,
        ledger_store=ledger_store,
        generation_store=generation_store,
    )
    assert mutated != expected
    assert len(mutated["knowledge"]) == 2
    assert len(mutated["ledger"]) == 2
    assert len(mutated["generations"]) == 2

    result = activate_runtime_sqlite_restore(
        backup_set_directory=backup.directory,
        targets=RuntimeSQLiteRestoreTargets(
            knowledge_database=knowledge_path,
            usage_cost_ledger_database=ledger_path,
            grounded_generation_database=generations_path,
        ),
    )

    assert result.backup_set_id == backup.backup_set_id
    assert set(result.restored_paths) == {
        knowledge_path.resolve(),
        ledger_path.resolve(),
        generations_path.resolve(),
    }

    restarted_knowledge_store = KnowledgeSQLiteStore(
        knowledge_path
    )
    restarted_ledger_store = GroundedProviderUsageCostLedgerSQLiteStore(
        ledger_path
    )
    restarted_generation_store = GroundedGenerationSQLiteStore(
        generations_path
    )

    restored = _read_all_state(
        knowledge_store=restarted_knowledge_store,
        ledger_store=restarted_ledger_store,
        generation_store=restarted_generation_store,
    )

    assert restored == expected
    assert restarted_knowledge_store.schema_version() == (
        KnowledgeSQLiteStore.SCHEMA_VERSION
    )
    assert restarted_ledger_store.schema_version() == (
        GroundedProviderUsageCostLedgerSQLiteStore.SCHEMA_VERSION
    )
    assert restarted_generation_store.schema_version() == (
        GroundedGenerationSQLiteStore.SCHEMA_VERSION
    )

    assert all(
        "after-backup" not in repr(rows)
        for rows in restored.values()
    )


def _write_pre_backup_state(
    *,
    knowledge_store: KnowledgeSQLiteStore,
    ledger_store: GroundedProviderUsageCostLedgerSQLiteStore,
    generation_store: GroundedGenerationSQLiteStore,
) -> None:
    with knowledge_store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO knowledge_records (
                knowledge_id,
                version,
                knowledge_type,
                subject_key,
                statement,
                valid_from,
                valid_to,
                generated_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "knowledge-before-backup",
                1,
                "FACT",
                "WORLD",
                "pre-backup knowledge statement",
                "2026-08-01T00:00:00+00:00",
                None,
                "2026-08-16T12:00:00+00:00",
                "ACTIVE",
            ),
        )
        connection.execute(
            """
            INSERT INTO knowledge_evidence (
                knowledge_id,
                version,
                evidence_order,
                evidence_type,
                evidence_id,
                observed_at,
                checksum_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "knowledge-before-backup",
                1,
                0,
                "REVIEW_PACKAGE",
                "review-before-backup",
                "2026-08-16T11:59:00+00:00",
                "abc123",
            ),
        )

    with ledger_store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO provider_usage_cost_ledger (
                request_id,
                provider_identity,
                model_identity,
                input_tokens,
                output_tokens,
                total_tokens,
                currency,
                input_cost,
                output_cost,
                total_cost,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "request-before-backup",
                "OPENAI",
                "gpt-test",
                10,
                5,
                15,
                "USD",
                "0.001",
                "0.002",
                "0.003",
                "2026-08-16T12:01:00+00:00",
            ),
        )

    with generation_store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO grounded_generations (
                request_id,
                generated_at,
                prompt_protocol_identity,
                answer_protocol_identity,
                provider_identity,
                model_identity,
                selected_knowledge_identities_json,
                cited_knowledge_identities_json,
                generation_json,
                trace_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "generation-before-backup",
                "2026-08-16T12:02:00+00:00",
                "PROMPT@1",
                "ANSWER@1",
                "OPENAI",
                "gpt-test",
                '["knowledge-before-backup@1"]',
                '["knowledge-before-backup@1"]',
                '{"answer":"pre-backup generation"}',
                '{"request_id":"generation-before-backup"}',
            ),
        )


def _write_post_backup_mutations(
    *,
    knowledge_store: KnowledgeSQLiteStore,
    ledger_store: GroundedProviderUsageCostLedgerSQLiteStore,
    generation_store: GroundedGenerationSQLiteStore,
) -> None:
    with knowledge_store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO knowledge_records (
                knowledge_id,
                version,
                knowledge_type,
                subject_key,
                statement,
                valid_from,
                valid_to,
                generated_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "knowledge-after-backup",
                1,
                "FACT",
                "WORLD",
                "after-backup mutation",
                "2026-08-16T12:31:00+00:00",
                None,
                "2026-08-16T12:31:00+00:00",
                "ACTIVE",
            ),
        )

    with ledger_store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO provider_usage_cost_ledger (
                request_id,
                provider_identity,
                model_identity,
                input_tokens,
                output_tokens,
                total_tokens,
                currency,
                input_cost,
                output_cost,
                total_cost,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "request-after-backup",
                "OPENAI",
                "gpt-test",
                20,
                10,
                30,
                "USD",
                "0.002",
                "0.004",
                "0.006",
                "2026-08-16T12:32:00+00:00",
            ),
        )

    with generation_store.transaction() as connection:
        connection.execute(
            """
            INSERT INTO grounded_generations (
                request_id,
                generated_at,
                prompt_protocol_identity,
                answer_protocol_identity,
                provider_identity,
                model_identity,
                selected_knowledge_identities_json,
                cited_knowledge_identities_json,
                generation_json,
                trace_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "generation-after-backup",
                "2026-08-16T12:33:00+00:00",
                "PROMPT@1",
                "ANSWER@1",
                "OPENAI",
                "gpt-test",
                '["knowledge-after-backup@1"]',
                '["knowledge-after-backup@1"]',
                '{"answer":"after-backup mutation"}',
                '{"request_id":"generation-after-backup"}',
            ),
        )


def _read_all_state(
    *,
    knowledge_store: KnowledgeSQLiteStore,
    ledger_store: GroundedProviderUsageCostLedgerSQLiteStore,
    generation_store: GroundedGenerationSQLiteStore,
) -> dict[str, tuple[tuple[object, ...], ...]]:
    return {
        "knowledge": _read_rows(
            knowledge_store,
            """
            SELECT
                knowledge_id,
                version,
                knowledge_type,
                subject_key,
                statement,
                valid_from,
                valid_to,
                generated_at,
                status
            FROM knowledge_records
            ORDER BY knowledge_id, version
            """,
        ),
        "knowledge_evidence": _read_rows(
            knowledge_store,
            """
            SELECT
                knowledge_id,
                version,
                evidence_order,
                evidence_type,
                evidence_id,
                observed_at,
                checksum_sha256
            FROM knowledge_evidence
            ORDER BY knowledge_id, version, evidence_order
            """,
        ),
        "ledger": _read_rows(
            ledger_store,
            """
            SELECT
                request_id,
                provider_identity,
                model_identity,
                input_tokens,
                output_tokens,
                total_tokens,
                currency,
                input_cost,
                output_cost,
                total_cost,
                recorded_at
            FROM provider_usage_cost_ledger
            ORDER BY request_id
            """,
        ),
        "generations": _read_rows(
            generation_store,
            """
            SELECT
                request_id,
                generated_at,
                prompt_protocol_identity,
                answer_protocol_identity,
                provider_identity,
                model_identity,
                selected_knowledge_identities_json,
                cited_knowledge_identities_json,
                generation_json,
                trace_json
            FROM grounded_generations
            ORDER BY request_id
            """,
        ),
    }


def _read_rows(
    store,
    sql: str,
) -> tuple[tuple[object, ...], ...]:
    with closing(store.connect()) as connection:
        rows = connection.execute(
            sql
        ).fetchall()

    return tuple(
        tuple(row)
        for row in rows
    )

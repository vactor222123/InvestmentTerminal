from datetime import datetime, timezone
import pytest

from investment_terminal.knowledge.models import KnowledgeEvidenceReference, KnowledgeRecord


def dt(day: int) -> datetime:
    return datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc)


def evidence(identifier: str = "snapshot-1") -> KnowledgeEvidenceReference:
    return KnowledgeEvidenceReference(
        evidence_type="HISTORICAL_SNAPSHOT",
        evidence_id=identifier,
        observed_at=dt(1),
        checksum_sha256="a" * 64,
    )


def record(**overrides) -> KnowledgeRecord:
    values = {
        "knowledge_id": "WORLD_ALLOCATION_CONTEXT",
        "knowledge_type": "FACT",
        "version": 1,
        "subject_key": "WORLD",
        "statement": "WORLD was present in the archived recommendation set.",
        "valid_from": dt(1),
        "valid_to": None,
        "generated_at": dt(2),
        "evidence": (evidence(),),
        "status": "ACTIVE",
    }
    values.update(overrides)
    return KnowledgeRecord(**values)


def test_record_is_versioned_traceable_and_serializable():
    item = record()
    assert item.identity_key == "WORLD_ALLOCATION_CONTEXT@1"
    assert item.is_open_ended is True
    assert item.to_dict()["evidence"][0]["identity_key"] == "HISTORICAL_SNAPSHOT:snapshot-1"


def test_multiple_distinct_evidence_references_supported():
    item = record(evidence=(
        evidence("snapshot-1"),
        KnowledgeEvidenceReference(
            evidence_type="SNAPSHOT_COMPARISON",
            evidence_id="comparison-1",
            observed_at=dt(2),
        ),
    ))
    assert len(item.evidence) == 2


def test_duplicate_evidence_identity_rejected():
    with pytest.raises(ValueError, match="unique identities"):
        record(evidence=(evidence("snapshot-1"), evidence("snapshot-1")))


def test_empty_evidence_rejected():
    with pytest.raises(ValueError, match="at least one reference"):
        record(evidence=())


def test_invalid_validity_interval_rejected():
    with pytest.raises(ValueError, match="valid_to must not be earlier"):
        record(valid_from=dt(3), valid_to=dt(2))


def test_unsupported_knowledge_type_rejected():
    with pytest.raises(ValueError, match="knowledge_type must be one of"):
        record(knowledge_type="PREDICTION")


def test_bad_checksum_rejected():
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        KnowledgeEvidenceReference(
            evidence_type="HISTORICAL_SNAPSHOT",
            evidence_id="snapshot-1",
            observed_at=dt(1),
            checksum_sha256="bad",
        )


def test_model_has_no_effectiveness_or_ai_semantics():
    data = record().to_dict()
    for key in ("confidence", "success_probability", "effectiveness", "ai_generated"):
        assert key not in data

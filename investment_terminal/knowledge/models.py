from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime


@dataclass(frozen=True, slots=True)
class KnowledgeEvidenceReference:
    evidence_type: str
    evidence_id: str
    observed_at: datetime
    checksum_sha256: str | None = None

    SUPPORTED_EVIDENCE_TYPES: ClassVar[tuple[str, ...]] = (
        "HISTORICAL_SNAPSHOT",
        "SNAPSHOT_COMPARISON",
        "HISTORICAL_REPLAY",
        "OUTCOME_RESEARCH",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_type", normalize_required_text(
            self.evidence_type, field_name="evidence_type", uppercase=True
        ))
        if self.evidence_type not in self.SUPPORTED_EVIDENCE_TYPES:
            raise ValueError("evidence_type must be one of: " + ", ".join(self.SUPPORTED_EVIDENCE_TYPES))
        object.__setattr__(self, "evidence_id", normalize_required_text(
            self.evidence_id, field_name="evidence_id"
        ))
        validate_aware_datetime(self.observed_at, field_name="observed_at")
        if self.checksum_sha256 is not None:
            checksum = self.checksum_sha256.strip().lower()
            if len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
                raise ValueError("checksum_sha256 must be a 64-character hexadecimal digest")
            object.__setattr__(self, "checksum_sha256", checksum)

    @property
    def identity_key(self) -> str:
        return f"{self.evidence_type}:{self.evidence_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "evidence_id": self.evidence_id,
            "identity_key": self.identity_key,
            "observed_at": self.observed_at.isoformat(),
            "checksum_sha256": self.checksum_sha256,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    knowledge_id: str
    knowledge_type: str
    version: int
    subject_key: str
    statement: str
    valid_from: datetime
    valid_to: datetime | None
    generated_at: datetime
    evidence: tuple[KnowledgeEvidenceReference, ...]
    status: str = "ACTIVE"

    SUPPORTED_KNOWLEDGE_TYPES: ClassVar[tuple[str, ...]] = ("FACT", "RELATIONSHIP", "PATTERN")
    SUPPORTED_STATUSES: ClassVar[tuple[str, ...]] = ("ACTIVE", "SUPERSEDED")

    def __post_init__(self) -> None:
        for name in ("knowledge_id", "subject_key", "statement"):
            object.__setattr__(self, name, normalize_required_text(
                getattr(self, name), field_name=name
            ))
        object.__setattr__(self, "knowledge_type", normalize_required_text(
            self.knowledge_type, field_name="knowledge_type", uppercase=True
        ))
        if self.knowledge_type not in self.SUPPORTED_KNOWLEDGE_TYPES:
            raise ValueError("knowledge_type must be one of: " + ", ".join(self.SUPPORTED_KNOWLEDGE_TYPES))
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version <= 0:
            raise ValueError("version must be a positive integer")
        validate_aware_datetime(self.valid_from, field_name="valid_from")
        validate_aware_datetime(self.generated_at, field_name="generated_at")
        if self.valid_to is not None:
            validate_aware_datetime(self.valid_to, field_name="valid_to")
            if self.valid_to < self.valid_from:
                raise ValueError("valid_to must not be earlier than valid_from")
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be a tuple")
        if not self.evidence:
            raise ValueError("evidence must contain at least one reference")
        if any(not isinstance(item, KnowledgeEvidenceReference) for item in self.evidence):
            raise TypeError("evidence must contain only KnowledgeEvidenceReference values")
        ids = tuple(item.identity_key for item in self.evidence)
        if len(set(ids)) != len(ids):
            raise ValueError("evidence references must have unique identities")
        object.__setattr__(self, "status", normalize_required_text(
            self.status, field_name="status", uppercase=True
        ))
        if self.status not in self.SUPPORTED_STATUSES:
            raise ValueError("status must be one of: " + ", ".join(self.SUPPORTED_STATUSES))

    @property
    def identity_key(self) -> str:
        return f"{self.knowledge_id}@{self.version}"

    @property
    def is_open_ended(self) -> bool:
        return self.valid_to is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_type": self.knowledge_type,
            "version": self.version,
            "identity_key": self.identity_key,
            "subject_key": self.subject_key,
            "statement": self.statement,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": None if self.valid_to is None else self.valid_to.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status,
            "is_open_ended": self.is_open_ended,
        }

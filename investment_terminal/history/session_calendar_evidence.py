"""Integrity verification for explicit session-calendar JSON evidence."""

import hashlib
import json
from datetime import datetime
from pathlib import Path


def verify_session_calendar_evidence(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    evidence = payload.get("evidence")
    sessions = payload.get("sessions")
    if not isinstance(evidence, dict):
        raise TypeError("evidence must be an object")
    if not isinstance(sessions, list):
        raise TypeError("sessions must be an array")
    required = ("source_uri", "retrieved_at", "sessions_sha256")
    for field in required:
        if not isinstance(evidence.get(field), str) or not evidence[field].strip():
            raise ValueError(f"evidence.{field} must be a non-empty string")
    retrieved_at = datetime.fromisoformat(
        evidence["retrieved_at"].replace("Z", "+00:00")
    )
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError("evidence.retrieved_at must be timezone-aware")
    serialized = json.dumps(
        sessions,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    actual = hashlib.sha256(serialized).hexdigest()
    expected = evidence["sessions_sha256"].strip().lower()
    if actual != expected:
        raise ValueError("session calendar evidence checksum mismatch")
    return {
        "source_uri": evidence["source_uri"].strip(),
        "retrieved_at": retrieved_at.isoformat(),
        "sessions_sha256": actual,
    }

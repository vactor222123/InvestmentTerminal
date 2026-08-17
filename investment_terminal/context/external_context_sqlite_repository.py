"""SQLite external-context repository adapter."""
import json, sqlite3
from datetime import datetime
from investment_terminal.context.external_context_models import ExternalContextEvidence, ExternalContextProvenance, ExternalContextQualityAssessment, ExternalContextRecord
from investment_terminal.context.external_context_repository import ExternalContextRepository
from investment_terminal.context.external_context_sqlite_store import ExternalContextSQLiteStore
from investment_terminal.utils.validation import normalize_required_text, validate_aware_datetime

class SQLiteExternalContextRepository(ExternalContextRepository):
    def __init__(self, store: ExternalContextSQLiteStore) -> None:
        if not isinstance(store, ExternalContextSQLiteStore): raise TypeError("store must be ExternalContextSQLiteStore")
        self.store=store
    def add(self, evidence):
        if not isinstance(evidence, ExternalContextEvidence): raise TypeError("evidence must be ExternalContextEvidence")
        p=evidence.provenance; payload=json.dumps(evidence.to_dict(),ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":"))
        try:
            with self.store.transaction() as c:
                c.execute("INSERT INTO external_context_evidence VALUES (?,?,?,?,?)",(evidence.record.context_id,p.source,p.source_record_id,p.published_at.isoformat(),payload))
                c.executemany("INSERT INTO external_context_subjects VALUES (?,?)",tuple((evidence.record.context_id,s.casefold()) for s in evidence.record.subjects))
        except sqlite3.IntegrityError as exc: raise ValueError("External context identity already exists") from exc
        return evidence
    def get(self, context_id):
        key=normalize_required_text(context_id,field_name="context_id"); rows=self._query("SELECT payload_json FROM external_context_evidence WHERE context_id=?",(key,)); return self._decode(rows[0]) if rows else None
    def list_all(self): return tuple(self._decode(r) for r in self._query("SELECT payload_json FROM external_context_evidence ORDER BY published_at,source,source_record_id,context_id"))
    def list_between(self,published_from,published_until):
        start=validate_aware_datetime(published_from,field_name="published_from"); end=validate_aware_datetime(published_until,field_name="published_until")
        if end<=start: raise ValueError("published_until must be later than published_from")
        return tuple(self._decode(r) for r in self._query("SELECT payload_json FROM external_context_evidence WHERE published_at>=? AND published_at<? ORDER BY published_at,source,source_record_id,context_id",(start.isoformat(),end.isoformat())))
    def list_by_subject(self,subject):
        key=normalize_required_text(subject,field_name="subject").casefold(); return tuple(self._decode(r) for r in self._query("SELECT e.payload_json FROM external_context_evidence e JOIN external_context_subjects s ON s.context_id=e.context_id WHERE s.subject_key=? ORDER BY e.published_at,e.source,e.source_record_id,e.context_id",(key,)))
    def _query(self,sql,args=()):
        self.store.initialize()
        with self.store.connect() as c: return c.execute(sql,args).fetchall()
    @staticmethod
    def _decode(row):
        x=json.loads(row["payload_json"]); r=x["record"]; p=x["provenance"]; q=x["quality"]
        return ExternalContextEvidence(ExternalContextRecord(r["context_id"],r["context_type"],r["title"],r["summary"],tuple(r["subjects"]),r["uncertainty_level"],tuple(r["uncertainty_reasons"]),datetime.fromisoformat(r["event_at"]) if r["event_at"] else None),ExternalContextProvenance(p["source"],p["source_record_id"],datetime.fromisoformat(p["published_at"]),datetime.fromisoformat(p["fetched_at"]),p["source_url"],p["checksum_sha256"]),ExternalContextQualityAssessment(q["status"],datetime.fromisoformat(q["checked_at"]),q["maximum_age_hours"],q["age_hours"],tuple(q["missing_provenance_fields"]),tuple(q["warnings"])))

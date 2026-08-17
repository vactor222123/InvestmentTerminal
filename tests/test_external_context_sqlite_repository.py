"""SQLite external-context persistence tests."""
from tests.test_external_context_repository import evidence, timestamp
from investment_terminal.context.external_context_sqlite_store import ExternalContextSQLiteStore
from investment_terminal.context.external_context_sqlite_repository import SQLiteExternalContextRepository

def test_sqlite_round_trip_restart_and_queries(tmp_path):
    path=tmp_path/"context.db"; repo=SQLiteExternalContextRepository(ExternalContextSQLiteStore(path))
    first=evidence("one",10,("EUR",)); second=evidence("two",11,("USD",))
    repo.add(second); repo.add(first)
    restarted=SQLiteExternalContextRepository(ExternalContextSQLiteStore(path))
    assert restarted.list_all()==(first,second)
    assert restarted.require("context-one")==first
    assert restarted.list_between(timestamp(10),timestamp(11))==(first,)
    assert restarted.list_by_subject("eur")== (first,)

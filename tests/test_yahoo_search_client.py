"""Tests for the bounded Yahoo Search adapter."""

import pytest

from investment_terminal.clients.yahoo_search_client import YahooSearchClient


def test_search_isin_disables_unrelated_content(monkeypatch):
    captured = {}

    class Search:
        def __init__(self, query, **kwargs):
            captured["query"] = query
            captured.update(kwargs)
            self.quotes = [{"symbol": "ABC.DE"}]

    monkeypatch.setattr("investment_terminal.clients.yahoo_search_client.yf.Search", Search)
    assert YahooSearchClient(timeout_seconds=7).search_isin(" de0000000001 ") == [
        {"symbol": "ABC.DE"}
    ]
    assert captured == {
        "query": "DE0000000001", "max_results": 25, "news_count": 0,
        "lists_count": 0, "include_cb": False, "include_nav_links": False,
        "include_research": False, "include_cultural_assets": False,
        "enable_fuzzy_query": False, "recommended": 0, "timeout": 7.0,
        "raise_errors": True,
    }


def test_search_isin_normalizes_provider_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private provider detail")
    monkeypatch.setattr("investment_terminal.clients.yahoo_search_client.yf.Search", fail)
    with pytest.raises(RuntimeError, match="ISIN search failed"):
        YahooSearchClient().search_isin("DE0000000001")


def test_search_isin_rejects_invalid_result(monkeypatch):
    class Search:
        def __init__(self, *args, **kwargs): self.quotes = ["invalid"]
    monkeypatch.setattr("investment_terminal.clients.yahoo_search_client.yf.Search", Search)
    with pytest.raises(RuntimeError, match="invalid data"):
        YahooSearchClient().search_isin("DE0000000001")


def test_search_symbol_uses_normalized_exact_query(monkeypatch):
    captured = {}

    class Search:
        def __init__(self, query, **kwargs):
            captured["query"] = query
            captured.update(kwargs)
            self.quotes = [{"symbol": "ABC", "currency": "USD"}]

    monkeypatch.setattr("investment_terminal.clients.yahoo_search_client.yf.Search", Search)
    result = YahooSearchClient(timeout_seconds=9).search_symbol(" abc ")
    assert result == [{"symbol": "ABC", "currency": "USD"}]
    assert captured["query"] == "ABC"
    assert captured["timeout"] == 9.0
    assert captured["news_count"] == 0

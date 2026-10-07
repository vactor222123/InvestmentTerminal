from dataclasses import replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from hashlib import sha256
import csv
import json

import pytest

from investment_terminal.cli.split_positions import main
from investment_terminal.market.corporate_actions import CorporateAction, CorporateActionSnapshot
from investment_terminal.market.split_adjustment import SplitPlan, SplitPriceBar, SplitPriceSeries, project_split_prices
from investment_terminal.portfolio.split_projection import project_split_positions
from investment_terminal.portfolio.transaction_csv_parser import PortfolioTransactionCsvParser
from investment_terminal.utils.atomic_write import write_json_atomic
from tests.test_position_reconstruction import WORLD, EM, ledger, trade


def at(day):
    return datetime(2026, 8, day, tzinfo=timezone.utc)


def snapshot(events=((5, 2),)):
    return CorporateActionSnapshot(
        "WORLD", at(1), at(20), at(21), "1.6.0", "EUR", "UTC", "ETF",
        19, at(1), at(19), False,
        tuple(CorporateAction(at(day), at(day).date().isoformat(), "SPLIT", ratio)
              for day, ratio in events),
    )


def plan(events=((5, 2),)):
    return SplitPlan(snapshot(events), "a" * 64, at(22), 7)


def project(source, schedule=None, basis="AS_TRADED"):
    return project_split_positions(source, schedule or plan(), instrument_key=WORLD.instrument_key,
                                   trade_basis=basis)


def prices():
    return SplitPriceSeries("WORLD", "EUR", "AS_TRADED", None, "b" * 64, (
        SplitPriceBar(at(4), 100, 120, 80, 110),
        SplitPriceBar(at(5), 50, 60, 40, 55),
        SplitPriceBar(at(6), 51, 61, 41, 56),
    ))


def test_price_split_preserves_source_and_does_not_adjust_effective_session_twice():
    original = prices()
    result = project_split_prices(original, plan())
    assert result.bars[0] == SplitPriceBar(at(4), 50, 60, 40, 55)
    assert result.bars[1:] == original.bars[1:]
    assert original.bars[0].close == 110
    assert project_split_prices(result, plan()) == result
    with pytest.raises(ValueError, match="different split evidence"):
        project_split_prices(result, plan(((5, 3),)))


@pytest.mark.parametrize("basis", ["UNKNOWN", "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT", "DIVIDEND_ADJUSTED", ""])
def test_unknown_or_dividend_price_basis_cannot_be_adjusted(basis):
    with pytest.raises(ValueError):
        replace(prices(), basis=basis)


@pytest.mark.parametrize("change", ["symbol", "currency", "end", "order", "duplicate", "window", "ohlc", "nan", "bool"])
def test_price_failure_paths(change):
    with pytest.raises((ValueError, TypeError)):
        series = prices()
        if change in ("symbol", "currency"):
            series = replace(series, **{change: "OTHER"})
        elif change == "end":
            series = replace(project_split_prices(series, plan()), basis_end=at(19))
        elif change == "order":
            series = replace(series, bars=tuple(reversed(series.bars)))
        elif change == "duplicate":
            series = replace(series, bars=(series.bars[0], series.bars[0]))
        else:
            bar = series.bars[0]
            bar = replace(bar, **({"timestamp": at(20)} if change == "window" else
                                  {"low": 200} if change == "ohlc" else
                                  {"close": float("nan") if change == "nan" else True}))
            series = replace(series, bars=(bar,))
        project_split_prices(series, plan())


def test_forward_split_sale_cost_and_repeat():
    source = ledger(trade("b", "BUY", 2, 10, 100), trade("s", "SELL", 6, 15, 60))
    original = source.to_dict()
    result = project(source)
    assert result.position.quantity == 5
    assert result.position.cost_basis == 250
    assert result.position.average_cost == 50
    assert result.realized_gain_loss == 150
    assert result.changed_trade_count == 1
    assert source.to_dict() == original
    assert project(source).to_dict() == result.to_dict()
    with pytest.raises(TypeError):
        project(result)


def test_reverse_split_retains_fractional_entitlement_without_cash_in_lieu():
    result = project(ledger(trade("b", "BUY", 2, 3, 100)), plan(((5, 0.1),)))
    assert result.position.quantity == 0.3
    assert result.position.cost_basis == 300
    assert result.position.average_cost == 1000


@pytest.mark.parametrize("events,expected", [(((5, 0.5),), 220), (((5, 2), (10, 3)), 110 / 6)])
def test_price_reverse_and_multiple_splits(events, expected):
    assert project_split_prices(prices(), plan(events)).bars[0].close == expected


@pytest.mark.parametrize("events", [((5, 1e300), (10, 1e300)), ((5, 1e-300), (10, 1e-300))])
def test_unrepresentable_split_products_fail_without_changing_inputs(events):
    original = prices()
    with pytest.raises((ValueError, OverflowError)):
        project_split_prices(original, plan(events))
    assert original.bars[0].close == 110


def test_zero_cost_trade_and_exact_freshness_boundary():
    schedule = replace(plan(), evaluated_at=at(28))
    result = project(ledger(trade("b", "BUY", 2, 1, 0)), schedule)
    assert result.position.quantity == 2
    assert result.position.cost_basis == result.position.average_cost == 0
    with pytest.raises(ValueError, match="stale"):
        replace(schedule, evaluated_at=at(28) + timedelta(microseconds=1))


def test_empty_selected_history_and_missing_opening_position_fail():
    with pytest.raises(ValueError, match="no trades"):
        project(ledger(trade("em", "BUY", 2, 1, 1, instrument=EM)))
    with pytest.raises(ValueError, match="exceeds"):
        project(ledger(trade("s", "SELL", 2, 1, 1)))


def test_price_duplicate_local_session_and_missing_basis_evidence_fail():
    series = prices()
    with pytest.raises(ValueError, match="Duplicate price session"):
        project_split_prices(replace(series, bars=(series.bars[0], replace(
            series.bars[0], timestamp=at(4) + timedelta(hours=1)))), plan())
    with pytest.raises(ValueError):
        replace(series, basis="SPLIT_ADJUSTED", basis_end=at(20))


def test_multiple_splits_sale_between_events_and_new_buy():
    source = ledger(trade("b", "BUY", 2, 10, 100), trade("s", "SELL", 6, 5, 60),
                    trade("b2", "BUY", 12, 2, 120))
    result = project(source, plan(((5, 2), (10, 0.5))))
    assert result.position.quantity == 9.5
    assert result.position.cost_basis == 990
    assert result.realized_gain_loss == 50


def test_fractional_ratio_and_exact_full_sale_leave_no_dust():
    result = project(ledger(trade("b", "BUY", 2, 0.2, 90), trade("s", "SELL", 6, 0.3, 70)),
                     plan(((5, 1.5),)))
    assert result.position is None
    assert result.realized_gain_loss == 3


def test_close_before_split_reopen_after_split_and_other_instrument_untouched():
    source = ledger(trade("b", "BUY", 2, 2, 100), trade("s", "SELL", 3, 2, 110),
                    trade("em", "BUY", 4, 9, 100, instrument=EM), trade("b2", "BUY", 6, 3, 60))
    result = project(source)
    assert result.position.quantity == 3 and result.position.cost_basis == 180
    assert result.realized_gain_loss == 20 and result.trade_count == 3


def test_dividends_do_not_change_split_factor_and_no_split_is_not_missing():
    value = snapshot(())
    value = replace(value, events=(CorporateAction(at(5), "2026-08-05", "DIVIDEND", 4),))
    schedule = SplitPlan(value, "a" * 64, at(22), 7)
    assert schedule.factor(at(2)) == 1
    assert project(ledger(trade("b", "BUY", 2, 2, 100)), schedule).position.quantity == 2
    assert schedule.to_dict()["action_completeness"] == "UNKNOWN"


@pytest.mark.parametrize("change", ["stale", "future", "age", "bool_age", "checksum", "duplicate_session"])
def test_invalid_split_evidence(change):
    with pytest.raises((ValueError, TypeError)):
        value = snapshot()
        now, age, pin = at(22), 7, "a" * 64
        if change == "stale": now = at(30)
        if change == "future": now = at(20)
        if change == "age": age = 0
        if change == "bool_age": age = True
        if change == "checksum": pin = "bad"
        if change == "duplicate_session":
            value = replace(value, events=(value.events[0], replace(value.events[0], timestamp=at(5) + timedelta(hours=1))))
        SplitPlan(value, pin, now, age)


@pytest.mark.parametrize("change", ["oversell", "same_day", "outside", "identity", "currency", "mapping", "adjusted"])
def test_portfolio_rejects_unsupported_or_ambiguous_evidence(change):
    with pytest.raises(ValueError):
        tx = trade("b", "BUY", 2, 10, 100)
        source = ledger(tx)
        schedule = plan()
        basis = "AS_TRADED"
        if change == "oversell": source = ledger(tx, trade("s", "SELL", 6, 21, 60))
        if change == "same_day": source = ledger(trade("b", "BUY", 5, 10, 100))
        if change == "outside": source = ledger(trade("b", "BUY", 20, 10, 100))
        if change == "identity": source = ledger(tx, trade("b2", "BUY", 6, 1, 60, instrument=replace(WORLD, name="Renamed")))
        if change == "currency": source = ledger(tx, trade("b2", "BUY", 6, 1, 60, currency="USD"))
        if change == "mapping": schedule = replace(schedule, snapshot=replace(schedule.snapshot, symbol="OTHER"))
        if change == "adjusted": basis = "SPLIT_ADJUSTED"
        project(source, schedule, basis)


def test_exchange_local_date_not_utc_midnight_controls_split():
    value = snapshot()
    value = replace(value, exchange_timezone="America/New_York",
                    events=(CorporateAction(at(5) + timedelta(hours=4), "2026-08-05", "SPLIT", 2),))
    schedule = SplitPlan(value, "a" * 64, at(22), 7)
    assert schedule.factor(at(5) + timedelta(hours=2), trade=True) == Fraction(2)
    with pytest.raises(ValueError, match="Split-day"):
        schedule.factor(at(5) + timedelta(hours=12), trade=True)


def cli_case(tmp_path):
    source = tmp_path / "trades.csv"
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PortfolioTransactionCsvParser.COLUMNS)
        writer.writeheader()
        writer.writerow(dict(transaction_id="b", transaction_type="BUY", occurred_at=at(2).isoformat(),
                             settlement_currency="EUR", symbol="WORLD", name=WORLD.name, instrument_type="ETF",
                             instrument_currency="EUR", isin=WORLD.isin, quantity="10", unit_price="100"))
    actions = tmp_path / "actions.json"
    write_json_atomic(actions, snapshot().to_dict())
    private, report = tmp_path / "private" / "result.json", tmp_path / "reports" / "result.json"
    args = ["--transactions", str(source), "--transactions-sha256", sha256(source.read_bytes()).hexdigest(),
            "--actions-snapshot", str(actions), "--actions-sha256", sha256(actions.read_bytes()).hexdigest(),
            "--instrument-key", WORLD.instrument_key, "--trade-basis", "AS_TRADED",
            "--actions-maximum-age-days", "7", "--private-output", str(private), "--report-output", str(report)]
    return args, source, actions, private, report


def test_cli_offline_projection_private_report_separation_and_repeat_refusal(tmp_path, capsys):
    args, source, actions, private, report = cli_case(tmp_path)
    original = (source.read_bytes(), actions.read_bytes())
    assert main(args, clock=lambda: at(22)) == 0
    data, redacted = json.loads(private.read_bytes()), json.loads(report.read_bytes())
    assert data["position"]["quantity"] == 20
    assert data["position"]["average_cost"] == 50
    assert redacted["status"] == "PROJECTED_WITH_LIMITATIONS"
    assert "WORLD" not in report.read_text() and WORLD.isin not in report.read_text()
    assert redacted["private_output_sha256"] == sha256(private.read_bytes()).hexdigest()
    assert (source.read_bytes(), actions.read_bytes()) == original
    before = (private.read_bytes(), report.read_bytes())
    assert main(args, clock=lambda: at(22)) == 1
    assert (private.read_bytes(), report.read_bytes()) == before
    assert not list(tmp_path.rglob("*.lock"))


@pytest.mark.parametrize("failure", ["checksum", "corrupt", "stale", "alias", "lock", "private_write", "report_write", "source_change", "private_readback", "report_readback", "late_private_change"])
def test_cli_failures_no_overwrite_or_false_completion(tmp_path, capsys, failure):
    args, source, actions, private, report = cli_case(tmp_path)
    writer = write_json_atomic
    now = at(22)
    if failure == "checksum": args[args.index("--transactions-sha256") + 1] = "0" * 64
    if failure == "corrupt":
        actions.write_bytes(b"{")
        args[args.index("--actions-sha256") + 1] = sha256(actions.read_bytes()).hexdigest()
    if failure == "stale": now = at(30)
    if failure == "alias": args[args.index("--private-output") + 1] = str(source)
    if failure == "lock":
        private.parent.mkdir()
        private.with_name(private.name + ".lock").write_text("owned")
    if failure in ("private_write", "report_write", "source_change"):
        def writer(path, payload):
            if path == (private if failure == "private_write" else report):
                if failure == "source_change": source.write_bytes(source.read_bytes() + b"\n")
                else: raise OSError("SECRET detail")
            write_json_atomic(path, payload)
    if failure in ("private_readback", "report_readback", "late_private_change"):
        def writer(path, payload):
            write_json_atomic(path, payload)
            if failure == "private_readback" and path == private:
                path.write_bytes(b"{}")
            if failure == "report_readback" and path == report:
                path.write_bytes(b"{}")
            if failure == "late_private_change" and path == report:
                private.write_bytes(b"{}")
    assert main(args, clock=lambda: now, writer=writer) == 1
    output = capsys.readouterr()
    assert "COMPLETE:" not in output.out and "SECRET" not in output.err
    if failure == "report_write": assert private.exists() and not report.exists()
    if failure == "lock": assert private.with_name(private.name + ".lock").read_text() == "owned"

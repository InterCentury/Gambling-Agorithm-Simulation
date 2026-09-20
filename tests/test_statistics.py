"""Tests for simulator.statistics."""
from decimal import Decimal

from simulator.engine import SimulationEngine
from simulator.models import SimulationConfig
from simulator.statistics import build_report


def make_config(**overrides) -> SimulationConfig:
    defaults = dict(
        initial_balance=Decimal("10000000"),
        initial_bet=Decimal("21000"),
        loss_multiplier=Decimal("3"),
        max_attempts=500,
        win_probability=0.5,
        random_seed=7,
    )
    defaults.update(overrides)
    return SimulationConfig(**defaults)


def test_report_win_loss_counts_match_attempts():
    result = SimulationEngine(make_config()).run()
    report = build_report(result)
    assert report.winloss.total_attempts == len(result.attempts)
    assert report.winloss.wins + report.winloss.losses == len(result.attempts)
    wins = sum(1 for a in result.attempts if a.result == "WIN")
    losses = sum(1 for a in result.attempts if a.result == "LOSS")
    assert report.winloss.wins == wins
    assert report.winloss.losses == losses


def test_report_financials_match_final_balance():
    result = SimulationEngine(make_config()).run()
    report = build_report(result)
    assert report.financial.final_balance == result.final_balance
    assert report.financial.net_profit_loss == result.final_balance - result.config.initial_balance


def test_report_bet_stats_within_bounds():
    result = SimulationEngine(make_config()).run()
    report = build_report(result)
    bets = [a.bet for a in result.attempts]
    assert report.financial.max_bet == max(bets)
    assert report.financial.min_bet == min(bets)
    assert report.financial.min_bet <= report.financial.average_bet <= report.financial.max_bet


def test_report_total_wagered_equals_sum_of_bets():
    result = SimulationEngine(make_config()).run()
    report = build_report(result)
    expected = sum((a.bet for a in result.attempts), Decimal("0"))
    assert report.financial.total_wagered == expected


def test_report_sequence_counts_match_engine():
    result = SimulationEngine(make_config()).run()
    report = build_report(result)
    assert report.winloss.completed_sequences == len(result.sequences)


def test_report_handles_empty_simulation():
    # A simulation that can't even afford its first bet.
    result = SimulationEngine(
        make_config(initial_balance=Decimal("100"), initial_bet=Decimal("21000"))
    ).run()
    report = build_report(result)
    assert report.winloss.total_attempts == 0
    assert report.financial.average_bet == Decimal("0")
    assert report.financial.max_bet == Decimal("0")

"""Tests for simulator.engine."""
from decimal import Decimal

import pytest

from simulator.engine import SimulationEngine
from simulator.models import SimulationConfig


def make_config(**overrides) -> SimulationConfig:
    defaults = dict(
        initial_balance=Decimal("10000000"),
        initial_bet=Decimal("21000"),
        loss_multiplier=Decimal("3"),
        max_attempts=100,
        win_probability=0.5,
        random_seed=42,
    )
    defaults.update(overrides)
    return SimulationConfig(**defaults)


def test_deterministic_seed_produces_identical_runs():
    cfg = make_config()
    result_a = SimulationEngine(cfg).run()
    result_b = SimulationEngine(cfg).run()
    seq_a = [(a.result, str(a.bet), str(a.balance_after)) for a in result_a.attempts]
    seq_b = [(a.result, str(a.bet), str(a.balance_after)) for a in result_b.attempts]
    assert seq_a == seq_b
    assert result_a.final_balance == result_b.final_balance


def test_different_seeds_can_diverge():
    result_a = SimulationEngine(make_config(random_seed=1)).run()
    result_b = SimulationEngine(make_config(random_seed=2)).run()
    seq_a = [a.result for a in result_a.attempts]
    seq_b = [a.result for a in result_b.attempts]
    # Not a strict guarantee, but with 100 attempts and different seeds the
    # sequences should not be identical.
    assert seq_a != seq_b


def test_losses_then_win_resets_sequence():
    cfg = make_config(max_attempts=10)
    engine = SimulationEngine(cfg)
    # Force a scripted outcome sequence: loss, loss, win.
    outcomes = iter([False, False, True])
    engine._outcome_gen.next_outcome = lambda: next(outcomes)

    records = []
    for record in engine.step_iter():
        records.append(record)
        if len(records) == 3:
            break

    loss1, loss2, win = records
    assert loss1.result == "LOSS"
    assert loss1.bet == cfg.initial_bet
    assert loss1.sequence_losses_after == cfg.initial_bet

    assert loss2.result == "LOSS"
    assert loss2.bet == cfg.initial_bet * cfg.loss_multiplier
    assert loss2.sequence_losses_after == loss1.sequence_losses_after + loss2.bet

    assert win.result == "WIN"
    # Winning bet should be 3x the second loss (still under the 100k threshold).
    assert win.bet == loss2.bet * cfg.loss_multiplier
    # Net result of a win equals the winning bet itself.
    assert win.net_result == win.bet
    # Sequence resets: engine's current_bet goes back to the initial bet.
    assert engine.current_bet == cfg.initial_bet
    assert engine.sequence_losses == Decimal("0")
    assert engine.loss_streak == 0

    # Sequence bookkeeping: the completed sequence's profit should equal
    # winning bet minus the two prior losses.
    assert len(engine.sequences) == 1
    seq = engine.sequences[0]
    assert seq.outcome == "WIN"
    assert seq.total_losses == loss1.bet + loss2.bet
    assert seq.profit == win.bet - (loss1.bet + loss2.bet)


def test_cumulative_loss_threshold_switches_multiplier():
    # Use a large initial bet and multiplier so we cross 100,000 quickly.
    cfg = make_config(
        initial_balance=Decimal("100000000"),
        initial_bet=Decimal("40000"),
        loss_multiplier=Decimal("3"),
        max_attempts=10,
    )
    engine = SimulationEngine(cfg)
    outcomes = iter([False, False, False, True])  # loss, loss, loss, win
    engine._outcome_gen.next_outcome = lambda: next(outcomes)

    records = []
    for record in engine.step_iter():
        records.append(record)
        if len(records) == 4:
            break

    loss1, loss2, loss3, win = records
    # loss1: bet 40,000 -> seq_losses 40,000 (<=100k) -> next bet x3 = 120,000
    assert loss1.multiplier_applied == "initial"
    assert loss2.bet == Decimal("120000.00")

    # loss2: bet 120,000 -> seq_losses 160,000 (>100k) -> next bet x2 = 240,000
    assert loss2.multiplier_applied == "secondary"
    assert loss3.bet == Decimal("240000.00")

    # loss3 remains over threshold -> secondary multiplier again
    assert loss3.multiplier_applied == "secondary"


def test_switch_from_3x_to_2x_exact_boundary():
    """Cumulative losses exactly at the threshold should still use the
    initial multiplier ('<=' per spec); only exceeding it switches."""
    cfg = make_config(
        initial_balance=Decimal("100000000"),
        initial_bet=Decimal("50000"),
        loss_multiplier=Decimal("3"),
        max_attempts=10,
        cumulative_loss_threshold=Decimal("100000"),
    )
    engine = SimulationEngine(cfg)
    outcomes = iter([False, False, True])
    engine._outcome_gen.next_outcome = lambda: next(outcomes)
    records = []
    for record in engine.step_iter():
        records.append(record)
        if len(records) == 2:
            break
    loss1, loss2 = records
    # seq_losses after loss1 = 50,000 (<=100,000) -> initial multiplier
    assert loss1.sequence_losses_after == Decimal("50000.00")
    assert loss1.multiplier_applied == "initial"
    assert loss2.bet == Decimal("150000.00")
    # seq_losses after loss2 = 200,000 (>100,000) -> secondary multiplier next
    assert loss2.sequence_losses_after == Decimal("200000.00")
    assert loss2.multiplier_applied == "secondary"


def test_insufficient_bankroll_terminates_safely():
    cfg = make_config(
        initial_balance=Decimal("50000"),
        initial_bet=Decimal("21000"),
        loss_multiplier=Decimal("3"),
        max_attempts=100,
    )
    engine = SimulationEngine(cfg)
    # Force two losses: 21,000 then bet becomes 63,000 which exceeds
    # the remaining balance of 29,000.
    outcomes = iter([False, False, False, False, False, False, False, False])
    engine._outcome_gen.next_outcome = lambda: next(outcomes)
    result = engine.run()

    assert result.termination_reason.startswith("Insufficient funds")
    assert result.insufficient_funds_events == 1
    # Balance should never go negative.
    assert result.final_balance >= 0
    assert all(a.balance_after >= 0 for a in result.attempts)


def test_starting_balance_smaller_than_initial_bet():
    cfg = make_config(
        initial_balance=Decimal("10000"),
        initial_bet=Decimal("21000"),
        max_attempts=10,
    )
    engine = SimulationEngine(cfg)
    result = engine.run()
    assert result.actual_attempts == 0
    assert result.termination_reason.startswith("Insufficient funds")
    assert result.final_balance == cfg.initial_balance


def test_max_attempts_reached_termination():
    cfg = make_config(max_attempts=5, initial_balance=Decimal("100000000"))
    engine = SimulationEngine(cfg)
    result = engine.run()
    assert result.actual_attempts == 5
    assert result.termination_reason == "Maximum attempts reached"


def test_balance_never_double_counts_winning_stake():
    """Regression test for the accounting requirement: a winning round's
    net effect on balance must be exactly +bet, not +2*bet or +bet with a
    separate deduction."""
    cfg = make_config(max_attempts=1, win_probability=0.999999, random_seed=1)
    engine = SimulationEngine(cfg)
    engine._outcome_gen.next_outcome = lambda: True
    result = engine.run()
    assert len(result.attempts) == 1
    win = result.attempts[0]
    assert win.balance_after - win.balance_before == cfg.initial_bet


def test_engine_is_single_use():
    cfg = make_config(max_attempts=5)
    engine = SimulationEngine(cfg)
    engine.run()
    with pytest.raises(RuntimeError):
        list(engine.step_iter())


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        make_config(initial_balance=Decimal("0"))
    with pytest.raises(ValueError):
        make_config(initial_bet=Decimal("-5"))
    with pytest.raises(ValueError):
        make_config(loss_multiplier=Decimal("1"))
    with pytest.raises(ValueError):
        make_config(win_probability=1.5)
    with pytest.raises(ValueError):
        make_config(max_attempts=0)

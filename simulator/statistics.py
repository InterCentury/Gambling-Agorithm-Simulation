"""Post-simulation statistics computation.

Everything in this module is derived strictly from the recorded
``AttemptRecord`` / ``SequenceRecord`` history in a ``SimulationResult`` --
no value here is invented or estimated outside of what the simulation
actually produced.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from .models import SimulationResult

EXTREME_LOSING_STREAK_THRESHOLD = 8  # illustrative cutoff for "extreme" streaks


def _dec_mean(values: List[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _dec_median(values: List[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal(2)


def _bucket_label(value: Decimal, signed: bool) -> str:
    magnitude = abs(value)
    if magnitude < 1_000:
        base = "< 1K"
    elif magnitude < 10_000:
        base = "1K - 10K"
    elif magnitude < 100_000:
        base = "10K - 100K"
    elif magnitude < 1_000_000:
        base = "100K - 1M"
    else:
        base = "> 1M"
    if signed:
        return f"{'Profit ' if value >= 0 else 'Loss '}{base}"
    return base


def _bucket_decimal(values: List[Decimal], *, signed: bool = False) -> Dict[str, int]:
    counts: "Counter[str]" = Counter(_bucket_label(v, signed) for v in values)
    return dict(counts)


@dataclass
class FinancialStats:
    starting_balance: Decimal
    final_balance: Decimal
    net_profit_loss: Decimal
    return_pct: float
    total_wagered: Decimal
    total_lost_on_losses: Decimal
    total_won_on_wins: Decimal
    average_bet: Decimal
    median_bet: Decimal
    min_bet: Decimal
    max_bet: Decimal
    largest_single_loss: Decimal
    largest_single_win: Decimal
    max_drawdown: Decimal
    max_drawdown_pct: float
    lowest_balance: Decimal
    critical_balance_events: int


@dataclass
class WinLossStats:
    total_attempts: int
    wins: int
    losses: int
    win_rate: float
    loss_rate: float
    longest_winning_streak: int
    longest_losing_streak: int
    average_losing_streak: float
    losing_streak_distribution: Dict[int, int]
    completed_sequences: int
    average_sequence_length: float
    longest_sequence: int
    shortest_sequence: int


@dataclass
class RecoveryStats:
    initial_multiplier_bets: int
    secondary_multiplier_bets: int
    sequences_ended_in_profit: int
    sequences_ended_in_loss: int
    average_sequence_profit: Decimal
    largest_sequence_profit: Decimal
    largest_sequence_loss: Decimal
    average_cumulative_losses_before_win: Decimal
    max_cumulative_losses_in_sequence: Decimal
    sequences_interrupted_by_insufficient_funds: int
    max_bet_distribution: Dict[str, int]


@dataclass
class RiskStats:
    max_drawdown: Decimal
    largest_single_exposure: Decimal
    largest_bet_pct_of_starting_balance: float
    attempts_bet_exceeded_balance: int
    insufficient_funds_terminations: int
    sequences_that_could_not_recover: int
    bankroll_survival_rate_pct: float
    extreme_losing_streak_count: int


@dataclass
class Distributions:
    bet_size_buckets: Dict[str, int]
    losing_streak_buckets: Dict[int, int]
    sequence_profit_buckets: Dict[str, int]
    balance_range_buckets: Dict[str, int]
    multiplier_usage: Dict[str, int]


@dataclass
class FullReport:
    financial: FinancialStats
    winloss: WinLossStats
    recovery: RecoveryStats
    risk: RiskStats
    distributions: Distributions


def build_report(result: SimulationResult) -> FullReport:
    attempts = result.attempts
    sequences = result.sequences
    cfg = result.config

    bets = [a.bet for a in attempts]
    wins = [a for a in attempts if a.result == "WIN"]
    losses = [a for a in attempts if a.result == "LOSS"]

    total_wagered = sum(bets, Decimal("0"))
    total_lost = sum((a.bet for a in losses), Decimal("0"))
    total_won = sum((a.bet for a in wins), Decimal("0"))

    net_profit = result.final_balance - cfg.initial_balance
    return_pct = float(net_profit / cfg.initial_balance * 100) if cfg.initial_balance else 0.0

    critical_threshold = cfg.initial_balance * Decimal("0.10")
    critical_events = sum(1 for a in attempts if a.balance_after <= critical_threshold)

    financial = FinancialStats(
        starting_balance=cfg.initial_balance,
        final_balance=result.final_balance,
        net_profit_loss=net_profit,
        return_pct=return_pct,
        total_wagered=total_wagered,
        total_lost_on_losses=total_lost,
        total_won_on_wins=total_won,
        average_bet=_dec_mean(bets),
        median_bet=_dec_median(bets),
        min_bet=min(bets, default=Decimal("0")),
        max_bet=max(bets, default=Decimal("0")),
        largest_single_loss=max((a.bet for a in losses), default=Decimal("0")),
        largest_single_win=max((a.bet for a in wins), default=Decimal("0")),
        max_drawdown=result.max_drawdown,
        max_drawdown_pct=result.max_drawdown_pct,
        lowest_balance=result.lowest_balance,
        critical_balance_events=critical_events,
    )

    # --- Win/loss streak analysis -------------------------------------
    longest_win_streak = 0
    longest_loss_streak = 0
    cur_win_streak = 0
    cur_loss_streak = 0
    losing_streak_lengths: List[int] = []
    running_loss_streak = 0
    for a in attempts:
        if a.result == "WIN":
            cur_win_streak += 1
            cur_loss_streak = 0
            longest_win_streak = max(longest_win_streak, cur_win_streak)
            if running_loss_streak > 0:
                losing_streak_lengths.append(running_loss_streak)
            running_loss_streak = 0
        else:
            cur_loss_streak += 1
            cur_win_streak = 0
            longest_loss_streak = max(longest_loss_streak, cur_loss_streak)
            running_loss_streak += 1
    if running_loss_streak > 0:
        losing_streak_lengths.append(running_loss_streak)

    losing_streak_dist: Dict[int, int] = dict(Counter(losing_streak_lengths))
    avg_losing_streak = (
        sum(losing_streak_lengths) / len(losing_streak_lengths) if losing_streak_lengths else 0.0
    )

    seq_lengths = [s.num_bets for s in sequences]
    winloss = WinLossStats(
        total_attempts=len(attempts),
        wins=len(wins),
        losses=len(losses),
        win_rate=(len(wins) / len(attempts) * 100) if attempts else 0.0,
        loss_rate=(len(losses) / len(attempts) * 100) if attempts else 0.0,
        longest_winning_streak=longest_win_streak,
        longest_losing_streak=longest_loss_streak,
        average_losing_streak=avg_losing_streak,
        losing_streak_distribution=losing_streak_dist,
        completed_sequences=len(sequences),
        average_sequence_length=(sum(seq_lengths) / len(seq_lengths)) if seq_lengths else 0.0,
        longest_sequence=max(seq_lengths, default=0),
        shortest_sequence=min(seq_lengths, default=0),
    )

    # --- Recovery strategy behaviour ------------------------------------
    initial_mult_bets = sum(1 for a in attempts if a.multiplier_applied == "initial")
    secondary_mult_bets = sum(1 for a in attempts if a.multiplier_applied == "secondary")
    won_sequences = [s for s in sequences if s.outcome == "WIN" and s.profit is not None]
    seq_profits = [s.profit for s in won_sequences if s.profit is not None]
    unresolved_sequences = [s for s in sequences if s.outcome != "WIN"]

    # A sequence "ended in loss" if it either completed with a
    # non-positive net profit, or never recovered at all (interrupted by
    # insufficient funds or the attempt cap) -- both represent bankroll
    # left worse off by that sequence.
    sequences_ended_in_loss = sum(1 for p in seq_profits if p <= 0) + len(unresolved_sequences)

    recovery = RecoveryStats(
        initial_multiplier_bets=initial_mult_bets,
        secondary_multiplier_bets=secondary_mult_bets,
        sequences_ended_in_profit=sum(1 for p in seq_profits if p > 0),
        sequences_ended_in_loss=sequences_ended_in_loss,
        average_sequence_profit=_dec_mean(seq_profits),
        largest_sequence_profit=max(seq_profits, default=Decimal("0")),
        largest_sequence_loss=min(seq_profits, default=Decimal("0")),
        average_cumulative_losses_before_win=_dec_mean([s.total_losses for s in won_sequences]),
        max_cumulative_losses_in_sequence=max((s.total_losses for s in sequences), default=Decimal("0")),
        sequences_interrupted_by_insufficient_funds=sum(
            1 for s in sequences if s.outcome == "INSUFFICIENT_FUNDS"
        ),
        max_bet_distribution=_bucket_decimal([s.max_bet for s in sequences]),
    )

    # --- Risk analysis ---------------------------------------------------
    largest_bet_pct = (
        float(result.largest_bet / cfg.initial_balance * 100) if cfg.initial_balance else 0.0
    )
    risk = RiskStats(
        max_drawdown=result.max_drawdown,
        largest_single_exposure=result.largest_bet,
        largest_bet_pct_of_starting_balance=largest_bet_pct,
        attempts_bet_exceeded_balance=result.insufficient_funds_events,
        insufficient_funds_terminations=(
            1 if result.termination_reason.startswith("Insufficient funds") else 0
        ),
        sequences_that_could_not_recover=len(unresolved_sequences),
        bankroll_survival_rate_pct=(
            (result.actual_attempts / result.requested_attempts * 100)
            if result.requested_attempts
            else 0.0
        ),
        extreme_losing_streak_count=sum(
            1 for length in losing_streak_lengths if length >= EXTREME_LOSING_STREAK_THRESHOLD
        ),
    )

    distributions = Distributions(
        bet_size_buckets=_bucket_decimal(bets),
        losing_streak_buckets=losing_streak_dist,
        sequence_profit_buckets=_bucket_decimal(seq_profits, signed=True),
        balance_range_buckets=_bucket_decimal([a.balance_after for a in attempts]),
        multiplier_usage={
            "Initial multiplier": initial_mult_bets,
            "Secondary (2x) multiplier": secondary_mult_bets,
        },
    )

    return FullReport(
        financial=financial,
        winloss=winloss,
        recovery=recovery,
        risk=risk,
        distributions=distributions,
    )

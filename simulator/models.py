"""Data models for the Triple Recovery Betting Strategy Simulator.

All monetary values use ``decimal.Decimal`` rather than ``float`` to avoid
binary floating-point rounding errors when balances are compounded over
thousands of attempts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass
class SimulationConfig:
    """User-configurable simulation parameters.

    Attributes:
        initial_balance: Starting bankroll.
        initial_bet: The first bet placed in every recovery sequence.
        loss_multiplier: Multiplier applied to the bet after a loss, while
            the current sequence's cumulative losses are at or below
            ``cumulative_loss_threshold``.
        max_attempts: Hard cap on the number of betting rounds simulated.
        win_probability: Probability (0-1 exclusive) that any given round
            is a win. Defaults to 0.5 (fair coin / even money).
        cumulative_loss_threshold: Sequence-loss level above which the
            engine switches from ``loss_multiplier`` to
            ``secondary_multiplier`` for future bets in that sequence.
        secondary_multiplier: Multiplier used once the threshold is
            exceeded. Fixed at 2x per the strategy specification, but
            exposed here for experimentation.
        random_seed: Optional seed for reproducible outcomes.
    """

    initial_balance: Decimal
    initial_bet: Decimal
    loss_multiplier: Decimal
    max_attempts: int
    win_probability: float = 0.5
    cumulative_loss_threshold: Decimal = Decimal("100000")
    secondary_multiplier: Decimal = Decimal("2")
    random_seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.initial_balance <= 0:
            raise ValueError("Initial balance must be greater than zero.")
        if self.initial_bet <= 0:
            raise ValueError("Initial bet must be greater than zero.")
        if self.loss_multiplier <= 1:
            raise ValueError("Loss multiplier must be greater than 1.")
        if self.secondary_multiplier <= 1:
            raise ValueError("Secondary multiplier must be greater than 1.")
        if self.max_attempts <= 0:
            raise ValueError("Maximum attempts must be greater than zero.")
        if not (0 < self.win_probability < 1):
            raise ValueError("Win probability must be strictly between 0 and 1.")
        if self.cumulative_loss_threshold <= 0:
            raise ValueError("Cumulative loss threshold must be greater than zero.")


@dataclass
class AttemptRecord:
    """A single simulated betting round."""

    attempt_number: int
    sequence_id: int
    bet: Decimal
    result: str  # "WIN" or "LOSS"
    balance_before: Decimal
    balance_after: Decimal
    sequence_losses_before: Decimal
    sequence_losses_after: Decimal
    net_result: Decimal
    loss_streak_after: int
    multiplier_applied: Optional[str] = None  # "initial" | "secondary" | None


@dataclass
class SequenceRecord:
    """A completed (or interrupted) recovery sequence: one or more bets
    that started at the initial bet and ended in a win, an
    insufficient-funds stop, or the simulation's max-attempts cutoff.
    """

    sequence_id: int
    start_attempt: int
    end_attempt: int
    num_bets: int
    total_losses: Decimal
    max_bet: Decimal
    outcome: str  # "WIN" | "INSUFFICIENT_FUNDS" | "INCOMPLETE"
    profit: Optional[Decimal] = None  # net result of the sequence; set for WIN


@dataclass
class SimulationResult:
    """The full output of a completed simulation run."""

    config: SimulationConfig
    attempts: List[AttemptRecord]
    sequences: List[SequenceRecord]
    final_balance: Decimal
    termination_reason: str
    requested_attempts: int
    actual_attempts: int
    duration_seconds: float
    insufficient_funds_events: int
    max_drawdown: Decimal
    max_drawdown_pct: float
    lowest_balance: Decimal
    largest_bet: Decimal

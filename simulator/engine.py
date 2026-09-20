"""Core simulation engine for the Triple Recovery Betting Strategy.

Balance transaction model
--------------------------
This is the single most important accounting rule in the engine, so it is
documented here as well as inline:

* On a LOSS: ``balance -= bet``. The full bet is deducted, and it is added
  to the running ``sequence_losses`` total for the current recovery
  sequence.
* On a WIN: ``balance += bet``. For an even-money bet, winning nets you
  an amount equal to the bet itself (you keep your stake and gain an
  equal amount). This is *not* a gross payout being added on top of a
  separately-deducted stake -- there is no separate stake deduction on a
  winning round at all. This avoids the classic double-counting bug
  where a winning stake is both "wagered" and "paid out" against the
  balance.

Because every round only ever applies a single ``+bet`` or ``-bet`` to
the balance, the net change in balance across an entire recovery
sequence is, by construction::

    Sequence Net Profit = Winning Bet - Sum(Previous Sequence Losses)

which matches the specification exactly, with no reconciliation step
required.

An ``OutcomeGenerator`` instance and a ``SimulationEngine`` instance are
each single-use: construct a fresh ``SimulationEngine`` for every run.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Iterator, List, Optional

from .models import AttemptRecord, SequenceRecord, SimulationConfig, SimulationResult
from .random_generator import OutcomeGenerator

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Round a Decimal to currency precision (2 decimal places)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class SimulationControl:
    """Runtime control flags for a live (UI-driven) simulation run."""

    stop_requested: bool = False
    paused: bool = False
    delay_seconds: float = 0.0


class SimulationEngine:
    """Runs the recovery betting strategy simulation.

    Usage::

        engine = SimulationEngine(config)
        result = engine.run()                      # batch mode
        # -- or --
        engine = SimulationEngine(config)
        result = engine.run_live(on_attempt, control)  # live/UI mode
    """

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self._outcome_gen = OutcomeGenerator(config.win_probability, config.random_seed)

        # Running state
        self.balance: Decimal = config.initial_balance
        self.current_bet: Decimal = config.initial_bet
        self.sequence_losses: Decimal = Decimal("0")
        self.loss_streak: int = 0
        self.sequence_id: int = 1
        self.sequence_start_attempt: int = 1
        self.sequence_max_bet: Decimal = config.initial_bet
        self.sequence_num_bets: int = 0

        self.attempts: List[AttemptRecord] = []
        self.sequences: List[SequenceRecord] = []

        self.termination_reason: str = "Maximum attempts reached"
        self.insufficient_funds_events: int = 0
        self.max_drawdown: Decimal = Decimal("0")
        self.lowest_balance: Decimal = config.initial_balance
        self.largest_bet: Decimal = Decimal("0")
        self._peak_balance: Decimal = config.initial_balance

        self._started = False
        self._finished = False

    # ------------------------------------------------------------------
    # Core generator: single source of truth for the simulation loop.
    # Both run() and run_live() consume this so the accounting logic
    # only exists in one place.
    # ------------------------------------------------------------------
    def step_iter(self) -> Iterator[AttemptRecord]:
        if self._started:
            raise RuntimeError("SimulationEngine instances are single-use. Create a new one.")
        self._started = True

        attempt_number = 0
        while attempt_number < self.config.max_attempts:
            attempt_number += 1

            if self.current_bet > self.balance:
                self.insufficient_funds_events += 1
                self._close_open_sequence(
                    outcome="INSUFFICIENT_FUNDS", end_attempt=attempt_number - 1
                )
                # Reset to the initial bet and start a fresh sequence so the
                # simulation can continue running to max_attempts.  We only
                # hard-stop if even the initial bet can't be covered (i.e. the
                # bankroll is truly exhausted).
                if self.config.initial_bet > self.balance:
                    self.termination_reason = (
                        f"Bankrupt: balance of {self.balance:,.2f} is below the "
                        f"initial bet of {self.config.initial_bet:,.2f} "
                        f"(attempt {attempt_number})."
                    )
                    break
                self.current_bet = self.config.initial_bet
                self.sequence_losses = Decimal("0")
                self.loss_streak = 0
                self.sequence_id += 1
                self.sequence_start_attempt = attempt_number
                self.sequence_max_bet = self.config.initial_bet
                self.sequence_num_bets = 0
                attempt_number -= 1  # don't consume this attempt number
                continue

            balance_before = self.balance
            seq_losses_before = self.sequence_losses
            bet = self.current_bet
            self.largest_bet = max(self.largest_bet, bet)
            self.sequence_max_bet = max(self.sequence_max_bet, bet)
            self.sequence_num_bets += 1

            is_win = self._outcome_gen.next_outcome()

            if is_win:
                record = self._process_win(attempt_number, bet, balance_before, seq_losses_before)
            else:
                record = self._process_loss(attempt_number, bet, balance_before, seq_losses_before)

            self.attempts.append(record)
            self._update_balance_extremes()
            yield record
        else:
            # Loop finished because max_attempts was reached, not via break.
            self._close_open_sequence(outcome="INCOMPLETE", end_attempt=attempt_number)

        self._finished = True

    def _process_win(
        self, attempt_number: int, bet: Decimal, balance_before: Decimal, seq_losses_before: Decimal
    ) -> AttemptRecord:
        net_result = bet
        self.balance = _money(self.balance + bet)
        record = AttemptRecord(
            attempt_number=attempt_number,
            sequence_id=self.sequence_id,
            bet=bet,
            result="WIN",
            balance_before=balance_before,
            balance_after=self.balance,
            sequence_losses_before=seq_losses_before,
            sequence_losses_after=Decimal("0"),
            net_result=net_result,
            loss_streak_after=0,
            multiplier_applied=None,
        )
        sequence_profit = net_result - seq_losses_before
        self.sequences.append(
            SequenceRecord(
                sequence_id=self.sequence_id,
                start_attempt=self.sequence_start_attempt,
                end_attempt=attempt_number,
                num_bets=self.sequence_num_bets,
                total_losses=seq_losses_before,
                max_bet=self.sequence_max_bet,
                outcome="WIN",
                profit=sequence_profit,
            )
        )
        # Reset for the next sequence.
        self.sequence_id += 1
        self.sequence_start_attempt = attempt_number + 1
        self.current_bet = self.config.initial_bet
        self.sequence_losses = Decimal("0")
        self.loss_streak = 0
        self.sequence_max_bet = self.config.initial_bet
        self.sequence_num_bets = 0
        return record

    def _process_loss(
        self, attempt_number: int, bet: Decimal, balance_before: Decimal, seq_losses_before: Decimal
    ) -> AttemptRecord:
        net_result = -bet
        self.balance = _money(self.balance - bet)
        self.sequence_losses = _money(self.sequence_losses + bet)
        self.loss_streak += 1

        if self.sequence_losses <= self.config.cumulative_loss_threshold:
            next_bet = _money(bet * self.config.loss_multiplier)
            multiplier_applied = "initial"
        else:
            next_bet = _money(bet * self.config.secondary_multiplier)
            multiplier_applied = "secondary"

        record = AttemptRecord(
            attempt_number=attempt_number,
            sequence_id=self.sequence_id,
            bet=bet,
            result="LOSS",
            balance_before=balance_before,
            balance_after=self.balance,
            sequence_losses_before=seq_losses_before,
            sequence_losses_after=self.sequence_losses,
            net_result=net_result,
            loss_streak_after=self.loss_streak,
            multiplier_applied=multiplier_applied,
        )
        self.current_bet = next_bet
        return record

    def _update_balance_extremes(self) -> None:
        self.lowest_balance = min(self.lowest_balance, self.balance)
        self._peak_balance = max(self._peak_balance, self.balance)
        drawdown = self._peak_balance - self.balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

    def _close_open_sequence(self, outcome: str, end_attempt: int) -> None:
        """Record the currently in-progress sequence as interrupted.

        No-op if there is no open sequence (e.g. the previous round was a
        WIN, which already closed and reset the sequence).
        """
        if self.sequence_num_bets == 0:
            return
        self.sequences.append(
            SequenceRecord(
                sequence_id=self.sequence_id,
                start_attempt=self.sequence_start_attempt,
                end_attempt=end_attempt,
                num_bets=self.sequence_num_bets,
                total_losses=self.sequence_losses,
                max_bet=self.sequence_max_bet,
                outcome=outcome,
                profit=None,
            )
        )

    # ------------------------------------------------------------------
    # Public run methods
    # ------------------------------------------------------------------
    def run(self) -> SimulationResult:
        """Run the simulation to completion without any live callbacks."""
        start = time.monotonic()
        for _ in self.step_iter():
            pass
        duration = time.monotonic() - start
        return self._build_result(duration)

    def run_live(
        self,
        on_attempt: Callable[[AttemptRecord, "SimulationEngine"], None],
        control: Optional[SimulationControl] = None,
    ) -> SimulationResult:
        """Run the simulation, invoking ``on_attempt`` after every round.

        ``control`` can be mutated concurrently (e.g. from a UI event
        handler) to pause or stop the run between attempts.
        """
        control = control or SimulationControl()
        start = time.monotonic()
        try:
            for record in self.step_iter():
                on_attempt(record, self)
                if control.delay_seconds:
                    time.sleep(control.delay_seconds)
                while control.paused and not control.stop_requested:
                    time.sleep(0.05)
                if control.stop_requested:
                    self.termination_reason = "Stopped by user"
                    self._close_open_sequence(
                        outcome="INCOMPLETE", end_attempt=record.attempt_number
                    )
                    break
        except KeyboardInterrupt:
            self.termination_reason = "Stopped by user (Ctrl+C)"
            if self.attempts:
                self._close_open_sequence(
                    outcome="INCOMPLETE", end_attempt=self.attempts[-1].attempt_number
                )
        duration = time.monotonic() - start
        return self._build_result(duration)

    def snapshot_result(self, duration: float = 0.0) -> SimulationResult:
        """Build a ``SimulationResult`` from current state at any point.

        Useful for producing a best-effort report after an external
        interrupt (e.g. Ctrl+C) that occurs outside of ``run``/``run_live``.
        """
        return self._build_result(duration)

    def _build_result(self, duration: float) -> SimulationResult:
        max_dd_pct = (
            float(self.max_drawdown / self.config.initial_balance * 100)
            if self.config.initial_balance
            else 0.0
        )
        return SimulationResult(
            config=self.config,
            attempts=self.attempts,
            sequences=self.sequences,
            final_balance=self.balance,
            termination_reason=self.termination_reason,
            requested_attempts=self.config.max_attempts,
            actual_attempts=len(self.attempts),
            duration_seconds=duration,
            insufficient_funds_events=self.insufficient_funds_events,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=max_dd_pct,
            lowest_balance=self.lowest_balance,
            largest_bet=self.largest_bet,
        )

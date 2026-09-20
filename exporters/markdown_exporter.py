"""Export a human-readable detailed report in Markdown."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from simulator.models import SimulationResult
from simulator.statistics import FullReport


def _money(v: Decimal) -> str:
    return f"{v:,.2f}"


def _pct(v: float) -> str:
    return f"{v:.2f}%"


def export_markdown(result: SimulationResult, report: FullReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = result.config
    f = report.financial
    w = report.winloss
    r = report.recovery
    k = report.risk
    d = report.distributions

    lines: list[str] = []
    lines.append("# Triple Recovery Betting Strategy - Simulation Report")
    lines.append("")
    lines.append(
        "> This report is the output of a random simulation for mathematical "
        "and risk-analysis purposes only. It does not prove the strategy is "
        "safe, profitable, or capable of recovering losses in general. Past "
        "or simulated results never guarantee future outcomes."
    )
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Attempts completed:** {result.actual_attempts:,} / {result.requested_attempts:,}")
    lines.append(f"- **Final balance:** {_money(result.final_balance)}")
    lines.append(f"- **Net profit/loss:** {_money(f.net_profit_loss)} ({_pct(f.return_pct)})")
    lines.append(f"- **Win rate:** {_pct(w.win_rate)}")
    lines.append(f"- **Maximum drawdown:** {_money(f.max_drawdown)} ({_pct(f.max_drawdown_pct)})")
    lines.append(f"- **Largest bet placed:** {_money(result.largest_bet)}")
    lines.append(f"- **Termination reason:** {result.termination_reason}")
    lines.append("")

    lines.append("## A. Simulation Configuration")
    lines.append("")
    lines.append(f"- Initial balance: {_money(cfg.initial_balance)}")
    lines.append(f"- Initial bet: {_money(cfg.initial_bet)}")
    lines.append(f"- Loss multiplier: {cfg.loss_multiplier}x")
    lines.append(f"- Cumulative-loss threshold for switch to secondary multiplier: {_money(cfg.cumulative_loss_threshold)}")
    lines.append(f"- Secondary multiplier: {cfg.secondary_multiplier}x")
    lines.append(f"- Win probability: {cfg.win_probability * 100:.2f}%")
    lines.append(f"- Requested attempts: {result.requested_attempts:,}")
    lines.append(f"- Actual attempts completed: {result.actual_attempts:,}")
    lines.append(f"- Random seed: {cfg.random_seed if cfg.random_seed is not None else 'None (nondeterministic)'}")
    lines.append(f"- Simulation duration: {result.duration_seconds:.3f}s")
    lines.append(f"- Termination reason: {result.termination_reason}")
    lines.append("")

    lines.append("## B. Financial Statistics")
    lines.append("")
    lines.append(f"- Starting balance: {_money(f.starting_balance)}")
    lines.append(f"- Final balance: {_money(f.final_balance)}")
    lines.append(f"- Net profit/loss: {_money(f.net_profit_loss)}")
    lines.append(f"- Return on initial balance: {_pct(f.return_pct)}")
    lines.append(f"- Total amount wagered: {_money(f.total_wagered)}")
    lines.append(f"- Total lost on losing rounds: {_money(f.total_lost_on_losses)}")
    lines.append(f"- Total won on winning rounds (gross winning payouts): {_money(f.total_won_on_wins)}")
    lines.append(f"- Average bet: {_money(f.average_bet)}")
    lines.append(f"- Median bet: {_money(f.median_bet)}")
    lines.append(f"- Minimum bet: {_money(f.min_bet)}")
    lines.append(f"- Maximum bet: {_money(f.max_bet)}")
    lines.append(f"- Largest single loss: {_money(f.largest_single_loss)}")
    lines.append(f"- Largest single win: {_money(f.largest_single_win)}")
    lines.append(f"- Maximum drawdown: {_money(f.max_drawdown)} ({_pct(f.max_drawdown_pct)})")
    lines.append(f"- Lowest balance reached: {_money(f.lowest_balance)}")
    lines.append(f"- Times balance dropped to <=10% of starting balance: {f.critical_balance_events:,}")
    lines.append("")
    lines.append(
        "*Note: total wagered, gross winning payouts, net profit/loss, and current "
        "bankroll are all reported separately above to avoid double-counting winning stakes.*"
    )
    lines.append("")

    lines.append("## C. Win/Loss Statistics")
    lines.append("")
    lines.append(f"- Total attempts: {w.total_attempts:,}")
    lines.append(f"- Wins: {w.wins:,}")
    lines.append(f"- Losses: {w.losses:,}")
    lines.append(f"- Win rate: {_pct(w.win_rate)}")
    lines.append(f"- Loss rate: {_pct(w.loss_rate)}")
    lines.append(f"- Longest winning streak: {w.longest_winning_streak}")
    lines.append(f"- Longest losing streak: {w.longest_losing_streak}")
    lines.append(f"- Average losing streak length: {w.average_losing_streak:.2f}")
    lines.append(f"- Completed recovery sequences: {w.completed_sequences:,}")
    lines.append(f"- Average sequence length: {w.average_sequence_length:.2f} bets")
    lines.append(f"- Longest sequence: {w.longest_sequence} bets")
    lines.append(f"- Shortest sequence: {w.shortest_sequence} bets")
    lines.append("")
    lines.append("### Losing Streak Length Distribution")
    lines.append("")
    lines.append("| Streak Length | Occurrences |")
    lines.append("|---|---|")
    for length in sorted(w.losing_streak_distribution):
        lines.append(f"| {length} | {w.losing_streak_distribution[length]:,} |")
    lines.append("")

    lines.append("## D. Recovery Strategy Statistics")
    lines.append("")
    lines.append(f"- Bets using the initial multiplier: {r.initial_multiplier_bets:,}")
    lines.append(f"- Bets using the secondary (2x) multiplier: {r.secondary_multiplier_bets:,}")
    lines.append(f"- Sequences that ended in profit: {r.sequences_ended_in_profit:,}")
    lines.append(f"- Sequences that ended in loss (interrupted/incomplete): {r.sequences_ended_in_loss:,}")
    lines.append(f"- Average sequence profit (won sequences): {_money(r.average_sequence_profit)}")
    lines.append(f"- Largest sequence profit: {_money(r.largest_sequence_profit)}")
    lines.append(f"- Largest sequence loss: {_money(r.largest_sequence_loss)}")
    lines.append(f"- Average cumulative losses before a win: {_money(r.average_cumulative_losses_before_win)}")
    lines.append(f"- Maximum cumulative losses reached in any sequence: {_money(r.max_cumulative_losses_in_sequence)}")
    lines.append(f"- Sequences interrupted by insufficient funds: {r.sequences_interrupted_by_insufficient_funds:,}")
    lines.append("")
    lines.append("### Maximum Bet per Sequence - Distribution")
    lines.append("")
    lines.append("| Range | Sequences |")
    lines.append("|---|---|")
    for label, count in r.max_bet_distribution.items():
        lines.append(f"| {label} | {count:,} |")
    lines.append("")

    lines.append("## E. Risk Analysis")
    lines.append("")
    lines.append(f"- Maximum drawdown: {_money(k.max_drawdown)}")
    lines.append(f"- Largest single exposure (biggest bet placed): {_money(k.largest_single_exposure)}")
    lines.append(f"- Largest bet as % of starting balance: {_pct(k.largest_bet_pct_of_starting_balance)}")
    lines.append(f"- Attempts where the next bet would have exceeded the balance: {k.attempts_bet_exceeded_balance:,}")
    lines.append(f"- Insufficient-funds terminations: {k.insufficient_funds_terminations}")
    lines.append(f"- Sequences that could not recover (interrupted): {k.sequences_that_could_not_recover:,}")
    lines.append(f"- Bankroll survival rate across requested attempts: {_pct(k.bankroll_survival_rate_pct)}")
    lines.append(f"- Extreme losing streaks (>= {8} losses in a row): {k.extreme_losing_streak_count:,}")
    lines.append("")
    lines.append(
        "**Important:** a finite simulation, however large, cannot establish "
        "that this strategy is safe, that it guarantees recovery of losses, "
        "or that it will be profitable in the long run. Results here reflect "
        "one realization of a random process under the configured parameters "
        "and random seed; a different seed or run length can produce "
        "materially different outcomes, including ruin."
    )
    lines.append("")

    lines.append("## F. Statistical Distributions")
    lines.append("")
    lines.append("### Bet Size Distribution")
    lines.append("")
    lines.append("| Range | Bets |")
    lines.append("|---|---|")
    for label, count in d.bet_size_buckets.items():
        lines.append(f"| {label} | {count:,} |")
    lines.append("")
    lines.append("### Sequence Profit Distribution")
    lines.append("")
    lines.append("| Range | Sequences |")
    lines.append("|---|---|")
    for label, count in d.sequence_profit_buckets.items():
        lines.append(f"| {label} | {count:,} |")
    lines.append("")
    lines.append("### Balance Range Distribution (after each attempt)")
    lines.append("")
    lines.append("| Range | Attempts |")
    lines.append("|---|---|")
    for label, count in d.balance_range_buckets.items():
        lines.append(f"| {label} | {count:,} |")
    lines.append("")
    lines.append("### Recovery Multiplier Usage")
    lines.append("")
    lines.append("| Multiplier | Times Used |")
    lines.append("|---|---|")
    for label, count in d.multiplier_usage.items():
        lines.append(f"| {label} | {count:,} |")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path

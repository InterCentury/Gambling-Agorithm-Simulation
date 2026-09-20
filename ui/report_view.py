"""Renders the comprehensive final statistics report to the terminal."""
from __future__ import annotations

from decimal import Decimal

from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from simulator.models import SimulationResult
from simulator.statistics import FullReport

from .styles import ACCENT, PANEL_BORDER, WARNING_STYLE, pnl_style


def _money(v: Decimal) -> str:
    return f"{v:,.2f}"


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", style="bold")
    table.add_column(justify="right")
    for k, v in rows:
        table.add_row(k, v)
    return table


def print_completion_banner(console: Console, result: SimulationResult) -> None:
    pnl = result.final_balance - result.config.initial_balance
    style = pnl_style(pnl)
    body = _kv_table(
        [
            ("Attempts Completed:", f"{result.actual_attempts:,} / {result.requested_attempts:,}"),
            ("Final Balance:", _money(result.final_balance)),
            ("Net Profit/Loss:", f"[{style}]{pnl:+,.2f}[/{style}]"),
            ("Maximum Drawdown:", f"{_money(result.max_drawdown)} ({result.max_drawdown_pct:.2f}%)"),
            ("Largest Bet:", _money(result.largest_bet)),
            ("Termination:", result.termination_reason),
        ]
    )
    console.print(
        Panel(
            body,
            title="[bold green]SIMULATION COMPLETE[/bold green]",
            border_style="green",
        )
    )


def _distribution_table(title: str, data: dict, count_label: str = "Count") -> Panel:
    table = Table(title=title, expand=True)
    table.add_column("Range")
    table.add_column(count_label, justify="right")
    for label, count in data.items():
        table.add_row(str(label), f"{count:,}")
    return Panel(table, border_style=PANEL_BORDER)


def print_full_report(console: Console, result: SimulationResult, report: FullReport) -> None:
    cfg = result.config
    f = report.financial
    w = report.winloss
    r = report.recovery
    k = report.risk
    d = report.distributions

    print_completion_banner(console, result)

    # --- A. Configuration -------------------------------------------------
    console.print(
        Panel(
            _kv_table(
                [
                    ("Initial Balance:", _money(cfg.initial_balance)),
                    ("Initial Bet:", _money(cfg.initial_bet)),
                    ("Loss Multiplier:", f"{cfg.loss_multiplier}x"),
                    ("Switch-to-2x Threshold:", _money(cfg.cumulative_loss_threshold)),
                    ("Secondary Multiplier:", f"{cfg.secondary_multiplier}x"),
                    ("Win Probability:", f"{cfg.win_probability * 100:.2f}%"),
                    ("Requested Attempts:", f"{result.requested_attempts:,}"),
                    ("Actual Attempts:", f"{result.actual_attempts:,}"),
                    ("Random Seed:", str(cfg.random_seed) if cfg.random_seed is not None else "None"),
                    ("Duration:", f"{result.duration_seconds:.3f}s"),
                    ("Termination Reason:", result.termination_reason),
                ]
            ),
            title="A. Simulation Configuration",
            border_style=PANEL_BORDER,
        )
    )

    # --- B. Financial -------------------------------------------------------
    console.print(
        Panel(
            _kv_table(
                [
                    ("Starting Balance:", _money(f.starting_balance)),
                    ("Final Balance:", _money(f.final_balance)),
                    ("Net Profit/Loss:", f"[{pnl_style(f.net_profit_loss)}]{f.net_profit_loss:+,.2f}[/{pnl_style(f.net_profit_loss)}]"),
                    ("Return on Initial Balance:", f"{f.return_pct:+.2f}%"),
                    ("Total Wagered:", _money(f.total_wagered)),
                    ("Total Lost (losing rounds):", _money(f.total_lost_on_losses)),
                    ("Total Won (winning rounds):", _money(f.total_won_on_wins)),
                    ("Average Bet:", _money(f.average_bet)),
                    ("Median Bet:", _money(f.median_bet)),
                    ("Min / Max Bet:", f"{_money(f.min_bet)} / {_money(f.max_bet)}"),
                    ("Largest Single Loss:", _money(f.largest_single_loss)),
                    ("Largest Single Win:", _money(f.largest_single_win)),
                    ("Maximum Drawdown:", f"[{WARNING_STYLE}]{_money(f.max_drawdown)} ({f.max_drawdown_pct:.2f}%)[/{WARNING_STYLE}]"),
                    ("Lowest Balance Reached:", _money(f.lowest_balance)),
                    ("Critical Balance Events (<=10%):", f"{f.critical_balance_events:,}"),
                ]
            ),
            title="B. Financial Statistics",
            border_style=PANEL_BORDER,
        )
    )

    # --- C. Win/Loss ----------------------------------------------------
    console.print(
        Panel(
            Group(
                _kv_table(
                    [
                        ("Total Attempts:", f"{w.total_attempts:,}"),
                        ("Wins / Losses:", f"{w.wins:,} / {w.losses:,}"),
                        ("Win / Loss Rate:", f"{w.win_rate:.2f}% / {w.loss_rate:.2f}%"),
                        ("Longest Winning Streak:", str(w.longest_winning_streak)),
                        ("Longest Losing Streak:", str(w.longest_losing_streak)),
                        ("Average Losing Streak:", f"{w.average_losing_streak:.2f}"),
                        ("Completed Sequences:", f"{w.completed_sequences:,}"),
                        ("Average Sequence Length:", f"{w.average_sequence_length:.2f} bets"),
                        ("Longest / Shortest Sequence:", f"{w.longest_sequence} / {w.shortest_sequence} bets"),
                    ]
                ),
            ),
            title="C. Win/Loss Statistics",
            border_style=PANEL_BORDER,
        )
    )

    # --- D. Recovery strategy -------------------------------------------
    console.print(
        Panel(
            _kv_table(
                [
                    ("Bets @ Initial Multiplier:", f"{r.initial_multiplier_bets:,}"),
                    ("Bets @ Secondary (2x) Multiplier:", f"{r.secondary_multiplier_bets:,}"),
                    ("Sequences Ended in Profit:", f"{r.sequences_ended_in_profit:,}"),
                    ("Sequences Ended in Loss:", f"{r.sequences_ended_in_loss:,}"),
                    ("Average Sequence Profit:", _money(r.average_sequence_profit)),
                    ("Largest Sequence Profit:", _money(r.largest_sequence_profit)),
                    ("Largest Sequence Loss:", _money(r.largest_sequence_loss)),
                    ("Avg. Cumulative Losses Before Win:", _money(r.average_cumulative_losses_before_win)),
                    ("Max Cumulative Losses in a Sequence:", _money(r.max_cumulative_losses_in_sequence)),
                    ("Sequences Interrupted (Insufficient Funds):", f"{r.sequences_interrupted_by_insufficient_funds:,}"),
                ]
            ),
            title="D. Recovery Strategy Statistics",
            border_style=PANEL_BORDER,
        )
    )

    # --- E. Risk ------------------------------------------------------------
    console.print(
        Panel(
            Group(
                _kv_table(
                    [
                        ("Maximum Drawdown:", _money(k.max_drawdown)),
                        ("Largest Single Exposure:", _money(k.largest_single_exposure)),
                        ("Largest Bet % of Starting Balance:", f"{k.largest_bet_pct_of_starting_balance:.2f}%"),
                        ("Attempts Where Bet Would Exceed Balance:", f"{k.attempts_bet_exceeded_balance:,}"),
                        ("Insufficient-Funds Terminations:", str(k.insufficient_funds_terminations)),
                        ("Sequences That Could Not Recover:", f"{k.sequences_that_could_not_recover:,}"),
                        ("Bankroll Survival Rate:", f"{k.bankroll_survival_rate_pct:.2f}% of requested attempts"),
                        ("Extreme Losing Streaks (>=8):", f"{k.extreme_losing_streak_count:,}"),
                    ]
                ),
                Padding(
                    Text(
                        "A finite simulation cannot establish that this strategy is safe, "
                        "guaranteed, or profitable in the long run. A different random seed "
                        "or a longer run can produce materially different results, including "
                        "ruin.",
                        style=f"italic {WARNING_STYLE}",
                    ),
                    (1, 0, 0, 0),
                ),
            ),
            title="E. Risk Analysis",
            border_style="red",
        )
    )

    # --- F. Distributions -------------------------------------------------
    console.print(_distribution_table("Bet Size Distribution", d.bet_size_buckets))
    console.print(_distribution_table("Losing Streak Length Distribution", w.losing_streak_distribution, "Occurrences"))
    console.print(_distribution_table("Sequence Profit Distribution", d.sequence_profit_buckets, "Sequences"))
    console.print(_distribution_table("Balance Range Distribution", d.balance_range_buckets, "Attempts"))
    console.print(_distribution_table("Recovery Multiplier Usage", d.multiplier_usage, "Times Used"))

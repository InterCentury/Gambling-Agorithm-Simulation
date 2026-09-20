"""Live terminal dashboard shown while the simulation runs."""
from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Deque, Optional

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from simulator.engine import SimulationControl, SimulationEngine
from simulator.models import AttemptRecord, SimulationConfig, SimulationResult

from .styles import ACCENT, LOSS_STYLE, PANEL_BORDER, TITLE_STYLE, WARNING_STYLE, WIN_STYLE, result_style

LOG_MAX_ROWS = 12


def _money(v: Decimal) -> str:
    return f"{v:,.2f}"


class Dashboard:
    """Owns the Rich ``Live`` display and renders it from engine state."""

    def __init__(self, config: SimulationConfig, console: Optional[Console] = None) -> None:
        self.config = config
        self.console = console or Console()
        self.log: Deque[AttemptRecord] = deque(maxlen=LOG_MAX_ROWS)
        self._latest: Optional[AttemptRecord] = None

    # ------------------------------------------------------------------
    def run(self, engine: SimulationEngine, control: SimulationControl) -> SimulationResult:
        with Live(
            self._render(engine), console=self.console, refresh_per_second=12, screen=False
        ) as live:
            def on_attempt(record: AttemptRecord, eng: SimulationEngine) -> None:
                self.log.append(record)
                self._latest = record
                live.update(self._render(eng))

            try:
                result = engine.run_live(on_attempt, control)
            except KeyboardInterrupt:
                control.stop_requested = True
                raise
            live.update(self._render(engine, finished=True))
        return result

    # ------------------------------------------------------------------
    def _render(self, engine: SimulationEngine, finished: bool = False) -> Panel:
        header = self._header()
        progress = self._progress_panel(engine)
        financial = self._financial_panel(engine)
        sequence = self._sequence_panel(engine)
        latest = self._latest_result_panel()
        log_table = self._log_panel()

        top_row = Table.grid(expand=True)
        top_row.add_column(ratio=1)
        top_row.add_column(ratio=1)
        top_row.add_row(financial, sequence)

        body = Group(progress, top_row, latest, log_table)
        status = "[dim]Press Ctrl+C to stop early and jump to the report.[/dim]"
        footer = Align.center(Text.from_markup(status)) if not finished else Align.center(
            Text.from_markup("[bold green]Simulation finished - preparing report...[/bold green]")
        )
        return Panel(
            Group(header, body, footer),
            border_style=PANEL_BORDER,
            title="[bold]Triple Recovery Betting Simulator[/bold]",
        )

    def _header(self) -> Align:
        return Align.center(
            Text("TRIPLE RECOVERY BETTING SIMULATOR", style=TITLE_STYLE, justify="center")
        )

    def _progress_panel(self, engine: SimulationEngine) -> Panel:
        total = self.config.max_attempts
        done = len(engine.attempts)
        pct = (done / total * 100) if total else 0.0
        bar = ProgressBar(total=total, completed=done, width=None)
        table = Table.grid(expand=True)
        table.add_column()
        table.add_row(f"Attempt: [bold]{done:,}[/bold] / {total:,}   ({pct:.2f}%)")
        table.add_row(bar)
        return Panel(table, title="Simulation Progress", border_style=PANEL_BORDER)

    def _financial_panel(self, engine: SimulationEngine) -> Panel:
        pnl = engine.balance - self.config.initial_balance
        pnl_style_ = WIN_STYLE if pnl >= 0 else LOSS_STYLE
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_row("Initial Balance:", _money(self.config.initial_balance))
        table.add_row("Current Balance:", f"[{ACCENT}]{_money(engine.balance)}[/{ACCENT}]")
        table.add_row("Total Profit/Loss:", f"[{pnl_style_}]{_money(pnl)}[/{pnl_style_}]")
        table.add_row("Current Bet:", _money(engine.current_bet))
        table.add_row("Largest Bet:", _money(engine.largest_bet))
        table.add_row("Maximum Drawdown:", f"[{WARNING_STYLE}]{_money(engine.max_drawdown)}[/{WARNING_STYLE}]")
        return Panel(table, title="Financial Overview", border_style=PANEL_BORDER)

    def _sequence_panel(self, engine: SimulationEngine) -> Panel:
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_row("Sequence ID:", str(engine.sequence_id))
        table.add_row("Sequence Losses:", _money(engine.sequence_losses))
        table.add_row("Current Losing Streak:", str(engine.loss_streak))
        threshold_note = (
            "secondary (2x)"
            if engine.sequence_losses > self.config.cumulative_loss_threshold
            else f"initial ({self.config.loss_multiplier}x)"
        )
        table.add_row("Active Multiplier:", threshold_note)
        table.add_row("Bets Placed This Sequence:", str(engine.sequence_num_bets))
        return Panel(table, title="Current Sequence", border_style=PANEL_BORDER)

    def _latest_result_panel(self) -> Panel:
        if self._latest is None:
            body = Text("Waiting for first attempt...", style="dim")
        else:
            a = self._latest
            style = result_style(a.result)
            table = Table.grid(padding=(0, 1))
            table.add_column(justify="left")
            table.add_column(justify="right")
            table.add_row("Attempt:", f"{a.attempt_number:,}")
            table.add_row("Bet:", _money(a.bet))
            table.add_row("Result:", f"[{style}]{a.result}[/{style}]")
            table.add_row("Net Result:", f"[{style}]{a.net_result:+,.2f}[/{style}]")
            body = table
        return Panel(body, title="Latest Result", border_style=PANEL_BORDER)

    def _log_panel(self) -> Panel:
        table = Table(expand=True, show_lines=False)
        table.add_column("Attempt", justify="right")
        table.add_column("Bet", justify="right")
        table.add_column("Result", justify="center")
        table.add_column("Balance", justify="right")
        table.add_column("Seq. Losses", justify="right")
        table.add_column("Net Result", justify="right")
        for a in self.log:
            style = result_style(a.result)
            table.add_row(
                f"{a.attempt_number:,}",
                _money(a.bet),
                f"[{style}]{a.result}[/{style}]",
                _money(a.balance_after),
                _money(a.sequence_losses_after),
                f"[{style}]{a.net_result:+,.2f}[/{style}]",
            )
        return Panel(table, title=f"Recent Attempts (last {LOG_MAX_ROWS})", border_style=PANEL_BORDER)

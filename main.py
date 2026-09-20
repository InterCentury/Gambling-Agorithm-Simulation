#!/usr/bin/env python3
"""Triple Recovery Betting Strategy Simulator - CLI entry point.

This program simulates a predefined betting recovery algorithm for
mathematical experimentation and risk analysis only. It does not connect
to any real-money betting service, and it does not claim the strategy
guarantees profit or eliminates risk.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from exporters.csv_exporter import export_csv
from exporters.json_exporter import export_json
from exporters.markdown_exporter import export_markdown
from simulator.engine import SimulationControl, SimulationEngine
from simulator.models import SimulationConfig
from simulator.statistics import build_report
from simulator.validation import (
    ValidationError,
    parse_money,
    parse_multiplier,
    parse_positive_int,
    parse_probability,
    parse_seed,
    parse_yes_no,
)
from ui.dashboard import Dashboard
from ui.report_view import print_full_report

REPORTS_DIR = Path(__file__).parent / "reports"


def prompt_field(console: Console, prompt_text: str, parser, default: str = "") -> object:
    """Repeatedly prompt until ``parser`` accepts the input."""
    while True:
        raw = Prompt.ask(prompt_text, default=default) if default else Prompt.ask(prompt_text)
        try:
            return parser(raw)
        except ValidationError as exc:
            console.print(f"[bold red]Invalid input:[/bold red] {exc}")


def gather_config(console: Console) -> SimulationConfig:
    console.print(
        Panel(
            "Configure the simulation. Press Enter to accept the shown default "
            "where one is offered.",
            title="Setup",
            border_style="cyan",
        )
    )

    initial_balance = prompt_field(
        console, "Initial Balance", lambda r: parse_money(r, "Initial balance"), default="10000000"
    )
    initial_bet = prompt_field(
        console, "Initial Bet", lambda r: parse_money(r, "Initial bet"), default="21000"
    )
    loss_multiplier = prompt_field(console, "Loss Multiplier", parse_multiplier, default="3")
    max_attempts = prompt_field(
        console,
        "Maximum Attempts",
        lambda r: parse_positive_int(r, "Maximum attempts", max_value=5_000_000),
        default="15000",
    )
    win_probability = prompt_field(
        console, "Win Probability % (default 50)", parse_probability, default="50"
    )
    seed = prompt_field(
        console, "Random Seed (blank for nondeterministic)", parse_seed, default=""
    )

    try:
        return SimulationConfig(
            initial_balance=initial_balance,
            initial_bet=initial_bet,
            loss_multiplier=loss_multiplier,
            max_attempts=max_attempts,
            win_probability=win_probability,
            random_seed=seed,
        )
    except ValueError as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        sys.exit(1)


def gather_run_options(console: Console) -> SimulationControl:
    delay_ms = prompt_field(
        console,
        "Visual delay between attempts in ms (0 = fastest, try 5-20 to watch it live)",
        lambda r: int(r) if r.strip() else 0,
        default="0",
    )
    if delay_ms < 0:
        delay_ms = 0
    return SimulationControl(delay_seconds=delay_ms / 1000.0)


def offer_exports(console: Console, result, report) -> None:
    do_export = prompt_field(
        console, "Export the report now? (y/n)", lambda r: parse_yes_no(r, default=True), default="y"
    )
    if not do_export:
        return

    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = REPORTS_DIR / f"simulation_{timestamp}.csv"
    json_path = REPORTS_DIR / f"simulation_{timestamp}.json"
    md_path = REPORTS_DIR / f"simulation_{timestamp}.md"

    export_csv(result, csv_path)
    export_json(result, report, json_path)
    export_markdown(result, report, md_path)

    console.print(
        Panel(
            f"[green]Exported:[/green]\n- {csv_path}\n- {json_path}\n- {md_path}",
            title="Export Complete",
            border_style="green",
        )
    )


def main() -> None:
    console = Console()
    console.print(
        Panel(
            "[bold]Triple Recovery Betting Strategy Simulator[/bold]\n"
            "For mathematical experimentation and risk analysis only. No real-money "
            "betting, gambling APIs, or external services are used.",
            border_style="cyan",
        )
    )

    config = gather_config(console)
    control = gather_run_options(console)

    engine = SimulationEngine(config)
    dashboard = Dashboard(config, console)

    console.print("\n[bold]Starting simulation...[/bold] (Ctrl+C to stop early)\n")
    try:
        result = dashboard.run(engine, control)
    except KeyboardInterrupt:
        result = engine.snapshot_result()  # best-effort partial result

    report = build_report(result)

    console.print("\n")
    print_full_report(console, result, report)

    offer_exports(console, result, report)

    console.print("\n[bold cyan]Done.[/bold cyan] Thank you for using the simulator.\n")


if __name__ == "__main__":
    main()

"""Shared Rich styling constants for the terminal UI."""

WIN_STYLE = "bold green"
LOSS_STYLE = "bold red"
WARNING_STYLE = "bold yellow"
INFO_STYLE = "bold cyan"
TITLE_STYLE = "bold white on dark_blue"
DIM_STYLE = "dim"
PANEL_BORDER = "bright_blue"
ACCENT = "bright_cyan"


def result_style(result: str) -> str:
    return WIN_STYLE if result == "WIN" else LOSS_STYLE


def pnl_style(value) -> str:
    return WIN_STYLE if value >= 0 else LOSS_STYLE

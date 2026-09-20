"""Export configuration, summary statistics, and full simulation data to JSON."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from simulator.models import SimulationResult
from simulator.statistics import FullReport


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def export_json(result: SimulationResult, report: FullReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "configuration": asdict(result.config),
        "summary": {
            "final_balance": result.final_balance,
            "termination_reason": result.termination_reason,
            "requested_attempts": result.requested_attempts,
            "actual_attempts": result.actual_attempts,
            "duration_seconds": result.duration_seconds,
            "insufficient_funds_events": result.insufficient_funds_events,
            "max_drawdown": result.max_drawdown,
            "max_drawdown_pct": result.max_drawdown_pct,
            "lowest_balance": result.lowest_balance,
            "largest_bet": result.largest_bet,
        },
        "statistics": {
            "financial": asdict(report.financial),
            "win_loss": asdict(report.winloss),
            "recovery": asdict(report.recovery),
            "risk": asdict(report.risk),
            "distributions": asdict(report.distributions),
        },
        "attempts": [asdict(a) for a in result.attempts],
        "sequences": [asdict(s) for s in result.sequences],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default)
    return path

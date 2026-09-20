"""Export the full attempt-by-attempt history to CSV."""
from __future__ import annotations

import csv
from pathlib import Path

from simulator.models import SimulationResult


def export_csv(result: SimulationResult, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "attempt_number",
        "sequence_id",
        "bet",
        "result",
        "balance_before",
        "balance_after",
        "sequence_losses_before",
        "sequence_losses_after",
        "net_result",
        "loss_streak_after",
        "multiplier_applied",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for a in result.attempts:
            writer.writerow(
                {
                    "attempt_number": a.attempt_number,
                    "sequence_id": a.sequence_id,
                    "bet": str(a.bet),
                    "result": a.result,
                    "balance_before": str(a.balance_before),
                    "balance_after": str(a.balance_after),
                    "sequence_losses_before": str(a.sequence_losses_before),
                    "sequence_losses_after": str(a.sequence_losses_after),
                    "net_result": str(a.net_result),
                    "loss_streak_after": a.loss_streak_after,
                    "multiplier_applied": a.multiplier_applied or "",
                }
            )
    return path

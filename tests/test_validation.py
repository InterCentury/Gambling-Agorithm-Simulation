"""Tests for simulator.validation and the export formats."""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from exporters.csv_exporter import export_csv
from exporters.json_exporter import export_json
from exporters.markdown_exporter import export_markdown
from simulator.engine import SimulationEngine
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


def test_parse_money_valid():
    assert parse_money("10000000", "Initial balance") == Decimal("10000000.00")
    assert parse_money("1,234.56", "field") == Decimal("1234.56")


def test_parse_money_rejects_zero_and_negative():
    with pytest.raises(ValidationError):
        parse_money("0", "field")
    with pytest.raises(ValidationError):
        parse_money("-5", "field")


def test_parse_money_rejects_garbage():
    with pytest.raises(ValidationError):
        parse_money("abc", "field")
    with pytest.raises(ValidationError):
        parse_money("", "field")


def test_parse_multiplier_accepts_x_suffix():
    assert parse_multiplier("3x") == Decimal("3")
    assert parse_multiplier("3") == Decimal("3")


def test_parse_multiplier_rejects_le_one():
    with pytest.raises(ValidationError):
        parse_multiplier("1")
    with pytest.raises(ValidationError):
        parse_multiplier("0.5")


def test_parse_positive_int_bounds():
    assert parse_positive_int("15,000", "Max attempts") == 15000
    with pytest.raises(ValidationError):
        parse_positive_int("0", "Max attempts")
    with pytest.raises(ValidationError):
        parse_positive_int("-1", "Max attempts")
    with pytest.raises(ValidationError):
        parse_positive_int("99999999999", "Max attempts", max_value=1000)


def test_parse_probability_variants():
    assert parse_probability("50") == 0.5
    assert parse_probability("50%") == 0.5
    assert parse_probability("0.5") == 0.5
    assert parse_probability("") == 0.5
    with pytest.raises(ValidationError):
        parse_probability("150")
    with pytest.raises(ValidationError):
        parse_probability("0")


def test_parse_seed():
    assert parse_seed("") is None
    assert parse_seed("42") == 42
    with pytest.raises(ValidationError):
        parse_seed("abc")


def test_parse_yes_no():
    assert parse_yes_no("y") is True
    assert parse_yes_no("n") is False
    assert parse_yes_no("") is True  # default
    with pytest.raises(ValidationError):
        parse_yes_no("maybe")


# ------------------------------------------------------------------
# Export format tests
# ------------------------------------------------------------------

def _run_small_simulation():
    config = SimulationConfig(
        initial_balance=Decimal("10000000"),
        initial_bet=Decimal("21000"),
        loss_multiplier=Decimal("3"),
        max_attempts=200,
        win_probability=0.5,
        random_seed=99,
    )
    result = SimulationEngine(config).run()
    report = build_report(result)
    return result, report


def test_csv_export_row_count(tmp_path: Path):
    result, _ = _run_small_simulation()
    path = export_csv(result, tmp_path / "out.csv")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    # header + one row per attempt
    assert len(lines) - 1 == len(result.attempts)


def test_json_export_is_valid_and_matches_balance(tmp_path: Path):
    result, report = _run_small_simulation()
    path = export_json(result, report, tmp_path / "out.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["summary"]["final_balance"] == pytest.approx(float(result.final_balance))
    assert len(data["attempts"]) == len(result.attempts)
    assert data["configuration"]["max_attempts"] == result.config.max_attempts


def test_markdown_export_contains_key_sections(tmp_path: Path):
    result, report = _run_small_simulation()
    path = export_markdown(result, report, tmp_path / "out.md")
    text = path.read_text(encoding="utf-8")
    for heading in [
        "Executive Summary",
        "A. Simulation Configuration",
        "B. Financial Statistics",
        "C. Win/Loss Statistics",
        "D. Recovery Strategy Statistics",
        "E. Risk Analysis",
        "F. Statistical Distributions",
    ]:
        assert heading in text


def test_exports_do_not_overwrite_with_distinct_timestamps(tmp_path: Path):
    result, report = _run_small_simulation()
    p1 = export_markdown(result, report, tmp_path / "simulation_2026-01-01_000000.md")
    p2 = export_markdown(result, report, tmp_path / "simulation_2026-01-01_000001.md")
    assert p1 != p2
    assert p1.exists() and p2.exists()

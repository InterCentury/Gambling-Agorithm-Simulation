"""Input validation and parsing helpers.

Every function here takes a raw string (as typed by a user at a prompt)
and returns a clean, correctly-typed value, or raises ``ValidationError``
with a message suitable for display directly to the user.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

# Guard rails against pathological input that would otherwise produce
# unusable (but not literally overflowing, since Decimal/int are
# arbitrary-precision in Python) simulations.
MAX_REASONABLE_MONEY = Decimal("1000000000000")  # 1 trillion
MAX_REASONABLE_ATTEMPTS = 5_000_000


class ValidationError(Exception):
    """Raised when user-supplied input fails validation."""


def parse_money(raw: str, field_name: str) -> Decimal:
    """Parse a positive currency amount."""
    cleaned = raw.strip().replace(",", "").replace("$", "")
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty.")
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a valid number.") from exc
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    if value > MAX_REASONABLE_MONEY:
        raise ValidationError(
            f"{field_name} of {value:,} is unreasonably large "
            f"(limit: {MAX_REASONABLE_MONEY:,})."
        )
    return value.quantize(Decimal("0.01"))


def parse_multiplier(raw: str, field_name: str = "Loss multiplier") -> Decimal:
    """Parse a multiplier expressed as '3', '3x', or '3.0'."""
    cleaned = raw.strip().lower().rstrip("x")
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty.")
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValidationError(f"{field_name} must be a valid number (e.g. 3 or 3x).") from exc
    if value <= 1:
        raise ValidationError(f"{field_name} must be greater than 1 (it must increase the bet).")
    if value > 1000:
        raise ValidationError(f"{field_name} of {value} is unreasonably large.")
    return value


def parse_positive_int(raw: str, field_name: str, *, max_value: Optional[int] = None) -> int:
    cleaned = raw.strip().replace(",", "")
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty.")
    try:
        value = int(cleaned)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a whole number.") from exc
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} cannot exceed {max_value:,}.")
    return value


def parse_probability(raw: str) -> float:
    """Parse a win probability given as '50', '50%', or '0.5'. Empty -> 0.5."""
    cleaned = raw.strip().rstrip("%")
    if not cleaned:
        return 0.5
    try:
        value = float(cleaned)
    except ValueError as exc:
        raise ValidationError("Win probability must be a number (e.g. 50 or 50%).") from exc
    if value > 1:
        value = value / 100.0
    if not (0 < value < 1):
        raise ValidationError("Win probability must be strictly between 0% and 100%.")
    return value


def parse_seed(raw: str) -> Optional[int]:
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ValidationError("Random seed must be a whole number.") from exc


def parse_yes_no(raw: str, default: bool = True) -> bool:
    cleaned = raw.strip().lower()
    if not cleaned:
        return default
    if cleaned in ("y", "yes", "true", "1"):
        return True
    if cleaned in ("n", "no", "false", "0"):
        return False
    raise ValidationError("Please answer yes or no (y/n).")

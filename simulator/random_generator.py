"""Deterministic random outcome generation.

Wrapping ``random.Random`` in its own class keeps the source of
randomness isolated and swappable (e.g. for testing with a fake
generator that returns a fixed sequence of outcomes).
"""
from __future__ import annotations

import random
from typing import Optional


class OutcomeGenerator:
    """Generates win/loss outcomes using a seeded PRNG for reproducibility.

    Two ``OutcomeGenerator`` instances constructed with the same
    ``win_probability`` and ``seed`` will always produce the same
    sequence of outcomes, which is what makes simulations reproducible.
    """

    def __init__(self, win_probability: float, seed: Optional[int] = None) -> None:
        if not (0 < win_probability < 1):
            raise ValueError("win_probability must be strictly between 0 and 1.")
        self.win_probability = win_probability
        self.seed = seed
        self._rng = random.Random(seed)

    def next_outcome(self) -> bool:
        """Return True for a win, False for a loss."""
        return self._rng.random() < self.win_probability

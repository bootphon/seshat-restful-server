from typing import List, Callable

from textgrid import Interval


def compute_tier_gamma(tier_a: List[Interval], tier_b: List[Interval], distance: Callable) -> float:
    """Computes the gamma coefficient between two tiers (https://hal.archives-ouvertes.fr/hal-01712281)"""
    pass
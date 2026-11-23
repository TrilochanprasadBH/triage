"""Statistics helpers for the triage project.

Only what the reports need. `ragkit` stage 07 carries the full argument for why these
exist; this is the same function, copied rather than imported so that each project stands
alone.
"""

from __future__ import annotations

import math


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a proportion."""
    if n <= 0:
        return (0.0, 1.0)

    p = successes / n
    denominator = 1 + (z * z) / n
    centre = p + (z * z) / (2 * n)
    margin = z * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))

    return (max(0.0, (centre - margin) / denominator), min(1.0, (centre + margin) / denominator))


def mcnemar_exact_p(n01: int, n10: int) -> float:
    """Two-sided exact McNemar p-value for paired pass/fail results.

    `n01` is where the first configuration passed and the second failed; `n10` is the
    reverse. Questions where both agree carry no information about which is better.
    """
    discordant = n01 + n10
    if discordant == 0:
        return 1.0
    k = max(n01, n10)
    tail = sum(math.comb(discordant, i) for i in range(k, discordant + 1)) / (2**discordant)
    return min(1.0, 2 * tail)

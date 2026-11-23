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

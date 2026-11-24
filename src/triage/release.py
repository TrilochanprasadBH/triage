"""Stage 07 — releasing a change safely.

Read `stages/07_release/README.md` first.

Three small functions. None of them is clever; together they are the difference between
discovering a regression on 1% of traffic and discovering it on all of it.

    bucket(ticket_id)                a stable number in 0..99
    assign(ticket_id, share)         "canary" or "control", deterministically
    decide(control, canary, tol)     promote or roll back, with the numbers attached
"""

from __future__ import annotations


def bucket(ticket_id: str) -> int:
    """Map a ticket id to a stable bucket in 0..99.

    Contract:
      - use SHA-256 of the ticket id, take the first 8 hex characters, convert to an int,
        and take it modulo 100
      - the same id always produces the same bucket, in every process and on every machine
      - do not use Python's built-in `hash()`, which is randomised per process
    """
    raise NotImplementedError("stage 07: implement bucket")


def assign(ticket_id: str, share: float) -> str:
    """Return "canary" for `share` of ids and "control" for the rest.

    Contract:
      - `share` is a fraction between 0 and 1
      - a ticket is in the canary when its bucket is below `share * 100`
      - assignment is stable: a ticket stays in the same arm across restarts
    """
    raise NotImplementedError("stage 07: implement assign")


def decide(
    control: list[int],
    canary: list[int],
    tolerance: float = 0.5,
) -> dict:
    """Promote or roll back, from two lists of scores.

    Contract:
      - compute the mean of each arm, and their difference (canary minus control)
      - roll back when the difference is below `-tolerance`
      - promote otherwise, including when the difference is small or positive
      - return a dict with keys: decision ("promote" or "rollback"), delta, control_mean,
        canary_mean, control_n, canary_n
      - with an empty arm, roll back: a release that produced no data is not a release

    The tolerance is the asymmetry. A regression is expensive and a neutral change is free, so
    the rule only objects to changes that are clearly worse. Without a tolerance, random
    variation rolls back good releases, which trains everyone to ignore the canary.
    """
    raise NotImplementedError("stage 07: implement decide")

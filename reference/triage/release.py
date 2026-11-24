"""Stage 07 reference: canary assignment and the release decision.

Three functions, and the interesting one is `decide`.

`bucket` uses SHA-256 rather than `hash()` because Python's string hash is salted per process.
A canary that reshuffles on every restart gives a user a different experience every deploy and
makes the two arms incomparable.

`decide` is deliberately asymmetric. It rolls back only on a clear regression, because the two
mistakes cost differently: shipping a regression affects every user who arrives before it is
noticed, while holding a neutral change costs one more day of the status quo. A symmetric rule
would flip on noise and teach the team to ignore the canary.
"""

from __future__ import annotations

import hashlib


def bucket(ticket_id: str) -> int:
    digest = hashlib.sha256(ticket_id.encode()).hexdigest()
    return int(digest[:8], 16) % 100


def assign(ticket_id: str, share: float) -> str:
    return "canary" if bucket(ticket_id) < share * 100 else "control"


def decide(control: list[int], canary: list[int], tolerance: float = 0.5) -> dict:
    if not control or not canary:
        return {
            "decision": "rollback",
            "delta": 0.0,
            "control_mean": sum(control) / len(control) if control else 0.0,
            "canary_mean": sum(canary) / len(canary) if canary else 0.0,
            "control_n": len(control),
            "canary_n": len(canary),
        }

    control_mean = sum(control) / len(control)
    canary_mean = sum(canary) / len(canary)
    delta = canary_mean - control_mean

    return {
        "decision": "rollback" if delta < -tolerance else "promote",
        "delta": round(delta, 2),
        "control_mean": round(control_mean, 2),
        "canary_mean": round(canary_mean, 2),
        "control_n": len(control),
        "canary_n": len(canary),
    }

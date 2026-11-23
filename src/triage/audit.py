"""Audit trail primitives.

Given, so the stage is about designing the record rather than about file I/O.

A trace record has to answer three questions about a decision, months later, without the
engineer who wrote the code:

  1. What did the system think, and on what basis? Intent, retrieved sections, the section
     it quoted.
  2. What did it do? The action, its arguments, and the outcome.
  3. Who allowed it? The approval, or nothing.

The field list below is the minimum. A record missing any of them can still be read, but it
cannot be replayed, and an unreplayable record is a story rather than evidence.
"""

from __future__ import annotations

import json
import pathlib

from .actions import World

REQUIRED = (
    "ticket_id",
    "intent",
    "retrieved",
    "quoted",
    "draft_text",
    "action",
    "action_args",
    "outcome",
    "approval",
)


def append(path: pathlib.Path, record: dict) -> None:
    """Append one record to a JSONL trace, creating the file if needed."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def read(path: pathlib.Path) -> list[dict]:
    path = pathlib.Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fresh_world() -> World:
    """The same starting state every replay begins from."""
    return World()


def explainability(record: dict) -> float:
    """Can the record explain *why*, not just *what*?

    Three fields carry the reasoning: the intent, the sections that were retrieved, and the
    one that was quoted. A record without them can say what happened and cannot say why,
    which is the difference between a log and an audit trail.
    """
    checks = (
        bool(record.get("intent")),
        bool(record.get("retrieved")),
        record.get("quoted") is not None or record.get("outcome") == "no_action",
    )
    return sum(checks) / len(checks)


def completeness(record: dict) -> float:
    """Fraction of required fields present. `None` counts as present when it is meaningful.

    `action`, `quoted` and `approval` are legitimately null in some records: a ticket that
    needs no action has no action. The field must still exist, which is what this checks.
    """
    present = sum(1 for field in REQUIRED if field in record)
    return present / len(REQUIRED)

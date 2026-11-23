"""Stage 05 — recording a decision, and replaying it.

Read `stages/05_audit/README.md` first.

Two functions. `record` runs the whole pipeline for one ticket and writes down everything
that determined the outcome. `replay` reproduces the outcome from the record alone — no
ticket text, no retrieval, no draft — which is what makes the record evidence rather than a
summary.
"""

from __future__ import annotations

import pathlib

from .actions import World
from .tickets import Ticket


def record(ticket: Ticket, world: World, index) -> dict:
    """Run the pipeline and return one trace record.

    Contract: the record contains every field in `audit.REQUIRED`, and the values are the
    ones the pipeline actually used:

      ticket_id     the ticket id
      intent        the label from `classify`
      retrieved     the section ids returned by `index.search(ticket, k=3)`, in order
      quoted        the section id the draft cited, or None when it escalated
      draft_text    the reply text
      action        the action name from `act`, or None
      action_args   the arguments passed to `execute`, or {}
      outcome       the gate outcome: executed, needs_approval, blocked, or no_action
      approval      None, because the agent never approves

    Use `audit.append` if you want to write it to disk as well; returning it is what the
    tests check.
    """
    raise NotImplementedError("stage 05: implement record")


def replay(record: dict) -> dict:
    """Reproduce the outcome from the record alone.

    Contract:
      - start from `audit.fresh_world()`
      - when `action` is None, return `{"outcome": "no_action", "state": snapshot}`
      - otherwise call `execute` with the recorded action, arguments and approval
      - return `{"outcome": ..., "state": world.snapshot()}`
      - do not consult the ticket, the index, or the draft

    The last clause is the whole point. A replay that re-runs retrieval is a rebuild, not a
    replay, and it will silently disagree with the original the day the corpus changes.
    """
    raise NotImplementedError("stage 05: implement replay")

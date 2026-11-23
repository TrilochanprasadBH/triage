"""Stage 05 reference: recording and replaying a decision.

The record is deliberately flat and boring. Every field is one that the pipeline actually
consumed or produced, and none of them is a summary written after the fact. The test for
whether a field belongs is simple: would replay disagree if it were missing? If yes, it is
part of the decision.

`replay` calls the same `execute` the live path called, against a world rebuilt from its
initial state. That is not a re-enactment: it is the same function, so a replay that
disagrees means the record was incomplete or the world's starting state changed.

One field is worth a note: `approval` is always None, because the agent never approves. If a
record ever contains an approval, it was produced by a human-in-the-loop path, and the
replay is expected to execute the dangerous action. That is how you can tell an authorised
refund from an unauthorised one six months later.
"""

from __future__ import annotations

from .actions import Approval, execute, extract_refs
from .agent import act
from .audit import fresh_world
from .classify import classify
from .compose import draft as compose
from .tickets import Ticket


def record(ticket: Ticket, world, index) -> dict:
    intent = classify(ticket)
    candidates = [section for section, _ in index.search(ticket, k=3)]
    reply = compose(ticket, candidates)
    decision = act(ticket, world)

    return {
        "ticket_id": ticket.id,
        "intent": intent,
        "retrieved": [section.id for section in candidates],
        "quoted": reply.citations[0] if reply.citations else None,
        "draft_text": reply.text,
        "action": decision.action,
        "action_args": extract_refs(ticket.message) if decision.action else {},
        "outcome": decision.outcome,
        "approval": None,
    }


def replay(record: dict) -> dict:
    world = fresh_world()

    if not record.get("action"):
        return {"outcome": "no_action", "state": world.snapshot()}

    approval = record.get("approval")
    approval_value = Approval(**approval) if approval else None
    result = execute(
        world,
        record["action"],
        record.get("action_args") or {},
        approval=approval_value,
    )
    return {"outcome": result["outcome"], "state": world.snapshot()}

"""A baseline record, given: the outcome and nothing else.

It is what most systems log. A line saying what happened, written after the fact, with no
record of the inputs, the retrieved sections, the arguments, or who approved anything.

It is enough to build a dashboard and useless for an incident review, which is what the
replay numbers show.
"""

from __future__ import annotations

from .agent import act
from .tickets import Ticket


def outcome_only(ticket: Ticket, world, index) -> dict:
    decision = act(ticket, world)
    return {
        "ticket_id": ticket.id,
        "action": decision.action,
        "outcome": decision.outcome,
    }

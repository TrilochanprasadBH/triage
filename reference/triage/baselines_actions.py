"""A baseline that proposes the most expensive action for everything, given.

It exists to separate two properties that are easy to confuse.

**Safety**: no dangerous action runs without approval. The baseline is perfectly safe,
because the gate is in `actions.execute` and the baseline cannot get around it.

**Quality**: the proposal is right for the ticket. The baseline is right whenever the answer
is a refund, which is about a fifth of the traffic, and wrong otherwise.

A system can be safe and useless at the same time, and this baseline is the proof.
"""

from __future__ import annotations

from .actions import World, execute, extract_refs
from .agent import Decision
from .tickets import Ticket


def refund_everything(ticket: Ticket, world: World) -> Decision:
    refs = extract_refs(ticket.message)
    result = execute(world, "issue_refund", refs, approval=None)
    return Decision(action="issue_refund", outcome=result["outcome"], detail=result.get("reason", ""))

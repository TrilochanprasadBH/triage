"""Stage 04 reference: choosing an action.

The reference is two things: a decision list that maps a ticket to at most one action, and a
single call into the gate with `approval=None`.

The decision list is deliberately boring. Every condition reads like a policy sentence, and
the order of the conditions is the only subtle part: "cancel the order I placed" is a
cancellation of an order, and the general cancellation rule would catch it first if the
specific rule were not above it.

The one judgement worth noting is the two-factor question. "How do I enable 2FA?" looks like
an access request and is documentation. Sending a reset link to someone asking for
instructions is harmless and wrong: it implies their account is broken.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .actions import World, execute, extract_refs
from .tickets import Ticket


@dataclass(frozen=True)
class Decision:
    action: str | None
    outcome: str
    detail: str = ""


HOW_TO = re.compile(r"\bhow (do|can) i\b|\bwhat is\b|\bwhere (are|is)\b|\bis there\b")


def choose_action(ticket: Ticket) -> str | None:
    message = ticket.message.casefold()
    intent = ticket.intent

    if intent == "cancel":
        if re.search(r"cancel (the )?order|before it ships|order \d", message):
            return "cancel_order"
        if re.search(r"cancel the refund", message):
            return None
        return "cancel_subscription"

    if intent == "refund":
        return "issue_refund"

    if intent == "billing":
        if re.search(r"invoice|receipt|vat", message):
            return "resend_invoice"
        return None

    if intent == "account":
        if HOW_TO.search(message) and "two-factor" in message:
            return None
        if re.search(r"log in|login|password|reset|locked|verify|two-factor|2fa", message):
            return "send_reset_link"
        return None

    if intent == "shipping":
        if re.search(r"change the delivery address|change my address", message):
            return None
        return "lookup_order"

    return None


def act(ticket: Ticket, world: World) -> Decision:
    name = choose_action(ticket)
    if name is None:
        return Decision(action=None, outcome="no_action")

    refs = extract_refs(ticket.message)
    result = execute(world, name, refs, approval=None)
    return Decision(action=name, outcome=result["outcome"], detail=result.get("reason", ""))

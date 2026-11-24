"""Candidate releases, given.

A release in this project is a change to how drafts are produced. Two candidates ship with
the stage, and neither is a strawman:

  **reword**  the same behaviour with different wording. The score should not move. Most
              prompt edits are like this, and a release process that rolls them back is as
              broken as one that ships regressions.

  **no_rule** a plausible "simplification": stop quoting the policy and send a friendly
              acknowledgment instead. It reads well, it is compliant, and it removes the one
              thing that makes the reply checkable, so every run loses its citation points.

The stage is not about producing better drafts. It is about deciding whether to ship one.
"""

from __future__ import annotations

from .compose import Draft, draft as current_draft
from .policy import Section
from .tickets import Ticket

REWORDED = {
    "refund": (
        "Hello, and thank you for contacting us about your refund. {rule} "
        "If you send your order number in reply, we will confirm what happens next."
    ),
    "shipping": (
        "Hello, and thank you for your patience regarding the delivery. {rule} "
        "Send your order number in reply if you would like a case opened with the courier."
    ),
    "billing": (
        "Hello, and thank you for raising this. {rule} "
        "Send the invoice number in reply and we will correct it."
    ),
    "account": (
        "Hello, and thank you for getting in touch. {rule} "
        "Reply here if you still cannot get in and we will verify your identity."
    ),
    "cancel": (
        "Hello, and thank you for letting us know. {rule} "
        "Reply if you would like the exact end date confirmed."
    ),
    "other": (
        "Hello, and thank you for your question. {rule} "
        "Reply if you need more detail on any part of this."
    ),
}

NO_RULE = {
    "refund": "Thanks for reaching out about your refund. We have logged your request and a member of the team will reply shortly.",
    "shipping": "Thanks for reaching out about the delivery. We have logged your request and a member of the team will reply shortly.",
    "billing": "Thanks for reaching out about billing. We have logged your request and a member of the team will reply shortly.",
    "account": "Thanks for reaching out about your account. We have logged your request and a member of the team will reply shortly.",
    "cancel": "Thanks for reaching out about your cancellation. We have logged your request and a member of the team will reply shortly.",
    "other": "Thanks for your question. We have logged it and a member of the team will reply shortly.",
}


def reword(ticket: Ticket, sections: list[Section]) -> Draft:
    """Same selection and same rule, different wording."""
    base = current_draft(ticket, sections)
    if base.escalated or not base.citations:
        return base
    from .checks import first_sentence

    chosen = next(section for section in sections if section.id == base.citations[0])
    template = REWORDED.get(ticket.intent or "other", REWORDED["other"])
    return Draft(
        text=template.format(rule=first_sentence(chosen.text)),
        citations=base.citations,
        escalated=False,
    )


def no_rule(ticket: Ticket, sections: list[Section]) -> Draft:
    """Drop the quotation, keep a polite acknowledgment."""
    if not sections:
        return current_draft(ticket, sections)
    template = NO_RULE.get(ticket.intent or "other", NO_RULE["other"])
    return Draft(text=template, citations=(), escalated=False)

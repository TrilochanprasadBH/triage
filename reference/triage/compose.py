"""Stage 03 reference: composing a cited draft.

Three decisions, and each one is a judgment you can disagree with.

**Quote the rule, do not paraphrase it.** The customer can check a quotation against the
policy. A paraphrase drifts: "within 30 days" becomes "about a month", and the support
agent who reads the draft next week cannot tell which rule it came from.

**Choose among the candidates instead of trusting the order.** Retrieval ranks by text
similarity to the whole message, and a general rule for the same intent often wins over
the specific one that applies. Re-scoring with a preference for the ticket's own intent,
then for distinctive word overlap, then for the original order, picks the specific rule
more often.

**Escalate rather than improvise.** With no candidates, the only honest reply is that a
human will take it. The tempting alternative — a generic "we will look into it" — is what
the baseline does, and it is why the baseline scores zero on rule coverage.

The templates are deliberately plain. A draft is a claim, and claims get checked; wit in a
support reply is a liability, not a feature.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .checks import first_sentence
from .policy import Section
from .tickets import Ticket

STOP = frozenset(
    """
    a an and are as at be been but by can could do does for from has have how i if in
    into is it its me my not of on or our please so that the their them then there
    these they this to us was we what when where which who why will with would you
    your about after before again still just now very
    """.split()
)

TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Draft:
    text: str
    citations: tuple[str, ...] = ()
    escalated: bool = False


TEMPLATES = {
    "refund": (
        "Thanks for getting in touch about your refund. {rule} "
        "Reply with your order number and we will confirm the next step."
    ),
    "shipping": (
        "Thanks for your patience about the delivery. {rule} "
        "Reply with your order number if you would like us to open a case with the courier."
    ),
    "billing": (
        "Thanks for flagging this. {rule} "
        "Reply with the invoice number and we will correct it."
    ),
    "account": (
        "Thanks for reaching out. {rule} "
        "Reply here if you still cannot get in and we will verify your identity."
    ),
    "cancel": (
        "Thanks for letting us know. {rule} "
        "Reply if you would like the exact end date confirmed."
    ),
    "other": (
        "Thanks for your question. {rule} "
        "Reply if you need more detail on any part of this."
    ),
}

ESCALATION = (
    "Thanks for reaching out. I could not find a policy that covers this request, so a "
    "member of the team will pick it up and reply within one business day."
)


def content_words(text: str) -> set[str]:
    return {token for token in TOKEN.findall(text.casefold()) if token not in STOP}


def choose(ticket: Ticket, sections: list[Section]) -> Section | None:
    """Prefer the ticket's own intent, then distinctive overlap, then retrieval order."""
    if not sections:
        return None

    message_words = content_words(ticket.message)
    best_index = 0
    best_key = None

    for index, section in enumerate(sections):
        title_words = content_words(section.title)
        body_words = content_words(section.text)
        # The title carries the rule's name. A message that says "duplicate charge"
        # matches the title of r2 exactly, and weight on the title is what makes that
        # beat a longer generic section that happens to share more body words.
        overlap = 3 * len(message_words & title_words) + len(message_words & body_words)
        key = (
            1 if section.intent == ticket.intent else 0,
            overlap,
            -index,
        )
        if best_key is None or key > best_key:
            best_key = key
            best_index = index

    return sections[best_index]


def draft(ticket: Ticket, sections: list[Section]) -> Draft:
    chosen = choose(ticket, sections)
    if chosen is None:
        return Draft(text=ESCALATION, citations=(), escalated=True)

    rule = first_sentence(chosen.text)
    template = TEMPLATES.get(ticket.intent or "other", TEMPLATES["other"])
    return Draft(
        text=template.format(rule=rule),
        citations=(chosen.id,),
        escalated=False,
    )

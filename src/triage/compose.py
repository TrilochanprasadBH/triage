"""Stage 03 — drafting a reply.

Read `stages/03_draft/README.md` first.

A draft is the first thing in this pipeline that a customer would actually read. It has to
do four things at once: state the rule that applies, avoid promising anything the policy
does not, cite only the right domain, and escalate when there is no rule to quote.

Return a `Draft`. The checks in `checks.py` are given, and they are what the score measures.
"""

from __future__ import annotations

from dataclasses import dataclass

from .policy import Section
from .tickets import Ticket


@dataclass(frozen=True)
class Draft:
    text: str
    citations: tuple[str, ...] = ()
    escalated: bool = False


def draft(ticket: Ticket, sections: list[Section]) -> Draft:
    """Compose a reply from the retrieved policy.

    Contract:
      - if `sections` is empty, escalate: return a `Draft` with `escalated=True`, no
        citations, and a message that says a human will pick it up. Do not invent a rule.
      - otherwise choose the single best section from the candidates and quote its first
        sentence verbatim, so that `checks.quotes_rule` passes
      - the citation tuple contains exactly the sections you quoted
      - cite nothing from another intent; `checks.focused` must pass
      - include a concrete next step the customer can take
      - never use a phrase from `checks.FORBIDDEN`

    Choosing the section is the actual work. Retrieval returns three candidates ordered by
    a score that knows nothing about drafting: the first one is often a general rule for
    the same intent when a specific one applies. Prefer the candidate whose own text
    shares the most distinctive words with the message, and whose intent matches.
    """
    raise NotImplementedError("stage 03: implement draft")

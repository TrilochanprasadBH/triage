"""A naive policy lookup, given as the baseline to beat.

It counts shared words between the message and the section, with no term weighting, no
length normalisation, and no use of the intent.

That last omission is the interesting one. The intent is already known, and ignoring it
means "cancel my order" and "cancel my subscription" are competing on vocabulary alone,
which they share almost completely.
"""

from __future__ import annotations

import re

from .policy import Section
from .tickets import Ticket


def keyword_sections(ticket: Ticket, sections: list[Section], k: int = 3) -> list[tuple[Section, float]]:
    words = set(re.findall(r"[a-z0-9]+", ticket.message.casefold()))
    scored = []
    for section in sections:
        section_words = set(re.findall(r"[a-z0-9]+", f"{section.title} {section.text}".casefold()))
        overlap = len(words & section_words)
        if overlap:
            scored.append((section, float(overlap)))
    scored.sort(key=lambda pair: (-pair[1], pair[0].id))
    return scored[:k]

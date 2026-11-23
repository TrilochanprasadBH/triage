"""A generic reply, given as the baseline to beat.

It is polite, it is compliant, and it answers nothing. Almost every first version of a
support assistant looks like this: a template that acknowledges the problem and promises
that someone will look into it.

It exists so the comparison is honest. A draft can score 100% on compliance with zero
information in it.
"""

from __future__ import annotations

from .compose import Draft
from .policy import Section
from .tickets import Ticket


def generic_reply(ticket: Ticket, sections: list[Section]) -> Draft:
    return Draft(
        text=(
            "Thanks for reaching out. We have received your message and will look into it. "
            "Someone from the team will get back to you shortly."
        ),
        citations=(),
    )

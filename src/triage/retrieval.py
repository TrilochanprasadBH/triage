"""Stage 02 — retrieving the policy that applies.

Read `stages/02_policy/README.md` first.

Stage 01 gave you an intent. This stage turns that intent plus the message into a short
list of policy sections, each of which is a rule you are allowed to quote.

Return sections, best first, and keep them few: stage 03 drafts a reply from them.
"""

from __future__ import annotations

from .policy import Section
from .tickets import Ticket


class PolicyIndex:
    """A searchable index over policy sections."""

    def __init__(self, sections: list[Section]) -> None:
        """Index the sections.

        Contract:
          - tokenise `title + text` for each section (lowercase, split on non-letters)
          - record term frequency per section, section length, and document frequency
          - store the average section length, for length normalisation
        """
        raise NotImplementedError("stage 02: implement PolicyIndex.__init__")

    def idf(self, term: str) -> float:
        """log(1 + (N - df + 0.5) / (df + 0.5)), the same form as everywhere else."""
        raise NotImplementedError("stage 02: implement PolicyIndex.idf")

    def search(self, ticket: Ticket, k: int = 3) -> list[tuple[Section, float]]:
        """Return up to `k` (section, score) pairs, highest score first.

        Contract:
          - score each section with BM25 over the ticket message: k1 = 1.5, b = 0.75
          - add a boost when `section.intent == ticket.intent`, because the intent is
            known before retrieval and a rule from another domain almost never applies
          - exclude sections with a score of zero
          - break ties by section id, so results are deterministic

        The boost is the whole lesson of this stage. Text similarity alone confuses
        "cancel my order" with "cancel my subscription", because both are cancellations.
        The intent does not: one is a shipping rule and one is a billing rule.
        """
        raise NotImplementedError("stage 02: implement PolicyIndex.search")

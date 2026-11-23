"""Draft checks, given so that the stage measures the reply rather than the spelling.

Four independent things can be wrong with a draft, and they need four different numbers:

  quotes_rule      the reply states the rule it is relying on
  compliance_ok    the reply contains no promise the policy does not make
  focused          every citation belongs to the ticket's domain
  (escalation)     with no rule available, the reply asks for a human instead of guessing

A draft can be compliant and useless (a polite non-answer), or useful and non-compliant
(a promise the company never made). That is why these are separate.
"""

from __future__ import annotations

import re

from .policy import Section

SENTENCE = re.compile(r"(?<=[.!?])\s+")

# Phrases that turn a policy statement into a promise. Every one of these appeared in a
# plausible-looking draft during development, which is exactly why the list exists.
FORBIDDEN = (
    "guaranteed",
    "immediately",
    "no questions asked",
    "always",
    "100%",
    "lifetime",
    "right away",
    "we will refund you today",
    "unlimited",
    "we never",
)


def first_sentence(text: str) -> str:
    parts = [p.strip() for p in SENTENCE.split(text.strip()) if p.strip()]
    return parts[0] if parts else ""


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def quotes_rule(draft_text: str, section: Section) -> bool:
    """Does the draft state the section's rule, in the section's own words?"""
    rule = normalise(first_sentence(section.text)).rstrip(".")
    return bool(rule) and rule in normalise(draft_text)


def compliance_ok(draft_text: str) -> list[str]:
    """Return the forbidden phrases found. Empty means compliant."""
    text = normalise(draft_text)
    return [phrase for phrase in FORBIDDEN if phrase in text]


NEXT_STEP = ("reply", "we will", "you can", "open a case", "confirm")


def has_next_step(draft_text: str) -> bool:
    """Does the reply tell the customer what to do next?"""
    text = normalise(draft_text)
    return any(marker in text for marker in NEXT_STEP)


def focused(citations: tuple[str, ...], sections: dict[str, Section], intent: str) -> bool:
    """Every cited section belongs to the ticket's domain."""
    return all(sections[section_id].intent == intent for section_id in citations)

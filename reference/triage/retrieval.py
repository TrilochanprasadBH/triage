"""Stage 02 reference: policy retrieval with an intent prior.

Two signals, in this order of importance.

**BM25 over the text.** Standard term weighting and length normalisation, the same
mechanics as `ragkit` stage 02, applied to 24 short policy sections instead of 362
documentation chunks.

**The intent as a prior.** Stage 01 already decided the ticket is a cancellation. Retrieval
does not need to rediscover that. Sections tagged with the same intent get a fixed boost,
which resolves the cases text alone gets wrong: "cancel my order" and "cancel my
subscription" share almost all their vocabulary, and only the intent separates a shipping
rule from a billing rule.

The boost is additive rather than multiplicative on purpose. Multiplying a BM25 score
amplifies short sections that already score highly; adding a constant is stable across the
score range and easy to reason about when you tune it.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .policy import Section
from .tickets import Ticket

TOKEN = re.compile(r"[a-z0-9]+")
INTENT_BOOST = 3.0
PREFIX_MIN = 5
TITLE_WEIGHT = 3
K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


class PolicyIndex:
    def __init__(self, sections: list[Section]) -> None:
        self.sections = list(sections)
        self.counts: dict[str, Counter] = {}
        self.lengths: dict[str, int] = {}
        self.df: Counter = Counter()

        for section in self.sections:
            # The title is the rule's name, so it is worth more than the body. Inflating
            # its term frequency is the cheapest way to say that without a second index.
            tokens = tokenize(section.text)
            counts = Counter(tokens)
            for term, count in Counter(tokenize(section.title)).items():
                counts[term] += count * TITLE_WEIGHT
            self.counts[section.id] = counts
            self.lengths[section.id] = len(tokens) + TITLE_WEIGHT * len(tokenize(section.title))
            for term in counts:
                self.df[term] += 1

        self.n = len(self.sections)
        self.avg_length = sum(self.lengths.values()) / self.n if self.n else 0.0

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, ticket: Ticket, k: int = 3) -> list[tuple[Section, float]]:
        terms = tokenize(ticket.message)
        if not terms:
            return []

        scored: list[tuple[Section, float]] = []
        for section in self.sections:
            counts = self.counts[section.id]
            length = self.lengths[section.id]

            score = 0.0
            for term in set(terms):
                tf = counts.get(term, 0)

                # Prefix matching, for stems the exact token misses. "cancel" must find
                # "cancellation" and "cancelling"; "deliver" must find "delivery". Only
                # applied to tokens of five characters or more, because short prefixes
                # ("ord") match far too much.
                if not tf and len(term) >= PREFIX_MIN:
                    tf = sum(count for token, count in counts.items() if token.startswith(term))

                if not tf:
                    continue
                normaliser = 1 - B + B * (length / self.avg_length if self.avg_length else 0)
                score += self.idf(term) * (tf * (K1 + 1) / (tf + K1 * normaliser))

            if score <= 0:
                continue
            if section.intent == ticket.intent:
                score += INTENT_BOOST
            scored.append((section, score))

        scored.sort(key=lambda pair: (-pair[1], pair[0].id))
        return scored[:k]

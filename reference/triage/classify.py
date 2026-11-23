"""Stage 01 reference: scored keyword classification.

The baseline matches the first intent list that fires, so the layout of the code decides
the answer. This version scores every intent and takes the maximum, with two refinements
that do most of the work:

**Specific phrases outweigh generic words.** "auto-renew" belongs to exactly one intent.
"account" belongs to several. A phrase that can only mean one thing should count double.

**Negative evidence is real.** "Not received" and "never arrived" look like shipping
words but describe a delivery failure, which is still shipping. "Charged after I
cancelled" is a refund request, not a cancellation, because the customer is asking for
money back. Reading the whole message and scoring it beats matching the first token.

This is still a keyword model. It is deliberately simple, it is inspectable, and it is
the right first thing to try: a rule set that scores 0.95 is easier to defend than a
model that scores 0.96 and cannot explain itself.
"""

from __future__ import annotations

from .tickets import Ticket

# Phrases that can only belong to one intent. Weight 2.
STRONG = {
    "refund": (
        "money back", "refund", "reimburse", "reverse the payment", "charged twice",
        "charged me twice", "duplicate charge",
    ),
    "shipping": (
        "tracking", "parcel", "courier", "in transit", "out for delivery",
        "never received", "not arrived", "has not arrived", "delivery address",
        "shipment", "delivered but",
    ),
    "billing": (
        "invoice", "vat invoice", "receipt", "billing address", "wrong amount",
        "wrong currency", "renewed early", "price changed", "tax twice", "quote",
        "card was declined", "billing details", "declined card",
    ),
    "account": (
        "log in", "login", "password", "two-factor", "2fa", "reset link",
        "username", "verify my email", "account is locked", "email address on my account",
    ),
    "cancel": (
        "cancel my subscription", "cancel the annual", "close my account",
        "end my subscription", "auto-renew", "do not renew", "not renew",
        "stop the monthly billing", "remove my account", "cancelling because",
        "before it ships", "cancel the refund", "end the subscription",
        "closed my account", "stop sending me invoices",
    ),
    "other": (
        "api", "discount", "offices", "language", "export my data", "uptime",
        "hiring", "nonprofit", "partner", "mobile app",
    ),
}

# Words that appear across intents. Weight 1.
WEAK = {
    "refund": ("money", "payment", "charged", "charge", "broken", "damaged"),
    "shipping": ("shipping", "package", "delivery", "deliver", "ships", "arrive",
                 "arrived", "tracking", "order"),
    "billing": ("billing", "charged", "charge", "price", "renewal", "tax",
                "subscription", "card", "currency"),
    "account": ("account", "profile", "email", "phone", "password", "verify"),
    "cancel": ("cancel", "cancelling", "canceled", "subscription", "leaving", "stop"),
    "other": ("support", "question"),
}

PRIORITY = ("refund", "shipping", "billing", "account", "cancel", "other")


def score(message: str, intent: str) -> int:
    """Weighted evidence for one intent.

    Strong phrases score 2 each, because each can only mean one intent. Weak words score
    1 **in total**, not 1 per match: "delivery arrived" trips three overlapping weak
    words and would otherwise outvote a specific phrase. Counting the fact of a weak
    match, rather than the number of synonyms it happens to contain, is the difference
    between evidence and repetition.
    """
    total = sum(2 for phrase in STRONG[intent] if phrase in message)
    if any(word in message for word in WEAK[intent]):
        total += 1
    return total


def classify(ticket: Ticket) -> str:
    message = ticket.message.casefold()

    scores = {intent: score(message, intent) for intent in PRIORITY}
    best = max(scores.values())
    if best == 0:
        return "other"

    # Ties are broken by priority order, which is stable and documented rather than
    # accidental. In practice ties are rare once strong phrases are weighted.
    for intent in PRIORITY:
        if scores[intent] == best:
            return intent
    return "other"

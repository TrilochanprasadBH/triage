"""A naive keyword classifier, given as the baseline to beat.

It checks the intents in a fixed order and returns the first one with a matching word.
That is the obvious first implementation, and it is wrong in a specific and instructive
way: order decides the answer. A ticket saying "please cancel order 8713 before it
ships" contains a shipping word and a cancellation word, and whichever list is checked
first wins.
"""

from __future__ import annotations

from .tickets import Ticket

ORDER = ("refund", "shipping", "billing", "account", "cancel")

KEYWORDS = {
    "refund": ("refund", "money back", "reimburse", "reverse the payment", "charged twice"),
    "shipping": ("shipping", "shipment", "parcel", "package", "tracking", "delivery",
                 "courier", "transit", "ships", "arrive", "arrived", "delivered"),
    "billing": ("invoice", "billing", "charged", "charge", "receipt", "vat",
                "currency", "price", "renewal", "renewed", "tax"),
    "account": ("log in", "login", "password", "email address", "phone number",
                "two-factor", "2fa", "locked", "verify", "username", "profile", "account"),
    "cancel": ("cancel", "close my account", "end my subscription", "auto-renew",
               "not renew", "remove my account", "stop the monthly billing", "leaving"),
}


def first_match(ticket: Ticket) -> str:
    message = ticket.message.casefold()
    for intent in ORDER:
        if any(word in message for word in KEYWORDS[intent]):
            return intent
    return "other"

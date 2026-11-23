"""Ticket records.

A ticket is a customer message plus the channel it arrived on. The intent label is only
present in the evaluation data; the classifier must not look at it.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

INTENTS = ("refund", "shipping", "billing", "account", "cancel", "other")


@dataclass(frozen=True)
class Ticket:
    id: str
    channel: str
    message: str
    intent: str | None = None
    split: str = "dev"
    gold_section: str | None = None

    def __post_init__(self) -> None:
        if self.intent is not None and self.intent not in INTENTS:
            raise ValueError(f"unknown intent {self.intent!r}")


def load_tickets(path: pathlib.Path) -> list[Ticket]:
    rows = [
        json.loads(line)
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [
        Ticket(
            id=row["id"],
            channel=row.get("channel", "email"),
            message=row["message"],
            intent=row.get("intent"),
            split=row.get("split", "dev"),
            gold_section=row.get("gold_section"),
        )
        for row in rows
    ]

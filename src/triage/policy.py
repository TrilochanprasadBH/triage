"""Policy documents.

A policy section is a rule, a short explanation, and the intent it belongs to. The intent
is metadata: it is known before retrieval (stage 01 produced it) and it is a strong signal
about which rules can possibly apply.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    id: str
    intent: str
    title: str
    text: str

    @property
    def label(self) -> str:
        return f"{self.intent}/{self.id} — {self.title}"


def load_policy(path: pathlib.Path) -> list[Section]:
    rows = [
        json.loads(line)
        for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [
        Section(id=row["id"], intent=row["intent"], title=row["title"], text=row["text"])
        for row in rows
    ]

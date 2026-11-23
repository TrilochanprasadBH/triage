#!/usr/bin/env python3
"""Verify the labels the other reports depend on.

    python evals/check_labels.py

Two invariants, both of which were violated at least once during development:

  1. every `gold_section` names a section that exists
  2. every `gold_section` belongs to the ticket's own intent

Invariant 2 is what makes `checks.focused` meaningful: a draft that stays inside the
ticket's domain can only ever cite its own intent. Two tickets needed a rule from another
domain (a renewal question answered by the auto-renew rule, a deletion request answered by
the data-deletion rule), so their `gold_section` is null and they are excluded from the
specificity metric rather than silently miscounted.

AGENTS.md requires every label to be verified programmatically before it is trusted. This
is that check.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from triage.policy import load_policy  # noqa: E402
from triage.tickets import load_tickets  # noqa: E402


def main() -> int:
    sections = {section.id: section for section in load_policy(ROOT / "evals" / "policy.jsonl")}
    tickets = load_tickets(ROOT / "evals" / "tickets.jsonl")

    problems: list[str] = []
    excluded = 0

    for ticket in tickets:
        if ticket.gold_section is None:
            excluded += 1
            continue
        section = sections.get(ticket.gold_section)
        if section is None:
            problems.append(f"{ticket.id}: gold_section {ticket.gold_section!r} does not exist")
            continue
        if section.intent != ticket.intent:
            problems.append(
                f"{ticket.id}: gold_section {section.id} is {section.intent}, ticket is {ticket.intent}"
            )

    print()
    print(f" tickets          {len(tickets)}")
    print(f" labelled         {len(tickets) - excluded}")
    print(f" excluded         {excluded} (cross-domain gold, see the docstring)")
    print(f" problems         {len(problems)}")
    for problem in problems:
        print(f"   {problem}")
    print()

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

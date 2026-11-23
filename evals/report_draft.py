#!/usr/bin/env python3
"""Drafting report.

    IMPL=reference python evals/report_draft.py
    python evals/report_draft.py --show-errors 6

Four numbers, because a draft can fail in four unrelated ways.

  specific citation   the draft quoted the section that governs this ticket
  rule quoted         the draft states that section's rule in its own words
  compliance          no promise the policy does not make
  focused             every citation belongs to the ticket's domain

The baseline is a generic "we will look into it" reply. It scores 100% on compliance and
zero on everything that makes a reply useful, which is the point of measuring separately.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.baselines_draft import generic_reply  # noqa: E402
from triage.checks import compliance_ok, focused, quotes_rule  # noqa: E402
from triage.compose import draft  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.tickets import load_tickets  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-errors", type=int, default=5)
    args = parser.parse_args()

    sections = load_policy(POLICY)
    by_id = {section.id: section for section in sections}
    tickets = [t for t in load_tickets(TICKETS) if t.intent and t.gold_section]
    dev = [t for t in tickets if t.split == "dev"]
    test = [t for t in tickets if t.split == "test"]

    index = PolicyIndex(sections)

    def run(drafter, subset):
        results = []
        for ticket in subset:
            candidates = [section for section, _ in index.search(ticket, k=3)]
            reply = drafter(ticket, candidates)
            gold = by_id[ticket.gold_section]
            results.append(
                {
                    "ticket": ticket,
                    "reply": reply,
                    "specific": ticket.gold_section in reply.citations,
                    "quoted": quotes_rule(reply.text, gold),
                    "violations": compliance_ok(reply.text),
                    "focused": focused(reply.citations, by_id, ticket.intent),
                    "escalated": reply.escalated,
                }
            )
        return results

    print()
    print(f" implementation {IMPL}")
    print(f" tickets        {len(tickets)} ({len(dev)} dev, {len(test)} held out)")
    print()

    for name, drafter in (
        ("baseline (generic reply)", generic_reply),
        ("cited draft", draft),
    ):
        print(f" {name}")
        for split_name, subset in (("dev", dev), ("test", test)):
            results = run(drafter, subset)
            n = len(results)
            specific = sum(r["specific"] for r in results) / n
            quoted = sum(r["quoted"] for r in results) / n
            compliant = sum(not r["violations"] for r in results) / n
            focus = sum(r["focused"] for r in results) / n
            print(
                f"   {split_name:<5} specific {specific:5.1%}  rule quoted {quoted:5.1%}  "
                f"compliant {compliant:5.1%}  focused {focus:5.1%}"
            )
            if split_name == "dev" and args.show_errors:
                misses = [r for r in results if not r["specific"]][: args.show_errors]
                for miss in misses:
                    ticket = miss["ticket"]
                    print(
                        f"      miss {ticket.id} gold={ticket.gold_section:<3} "
                        f"cited={list(miss['reply'].citations)}  {ticket.message[:44]}"
                    )
        print()

    violations = []
    for ticket in tickets:
        candidates = [section for section, _ in index.search(ticket, k=3)]
        reply = draft(ticket, candidates)
        found = compliance_ok(reply.text)
        if found:
            violations.append((ticket.id, found))
    if violations:
        print(f" compliance violations: {len(violations)}")
        for ticket_id, found in violations[:5]:
            print(f"   {ticket_id} {found}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Drafting report.

    IMPL=reference python3 evals/report_draft.py
    python3 evals/report_draft.py      # works before you have written anything

Four properties, because a draft can fail in four unrelated ways:

  specific citation   the draft quoted the section that governs this ticket
  rule quoted         the draft states that section's rule in its own words
  compliance          no promise the policy does not make
  focused             every citation belongs to the ticket's domain

Plus the escalation count, because "escalate rather than improvise" is a behaviour and
behaviours need a number.
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
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.stats import mcnemar_exact_p, wilson_interval  # noqa: E402
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

    try:
        from triage.compose import draft
    except NotImplementedError:
        draft = None

    try:
        index = PolicyIndex(sections)
        index.search(dev[0], k=1)
    except NotImplementedError:
        print()
        print(" implementation " + IMPL)
        print(" retrieval is not implemented yet, so drafting cannot be measured.")
        print()
        return 0

    def run(drafter, subset):
        rows = []
        for ticket in subset:
            candidates = [section for section, _ in index.search(ticket, k=3)]
            reply = drafter(ticket, candidates)
            gold = by_id[ticket.gold_section]
            rows.append(
                {
                    "ticket": ticket,
                    "reply": reply,
                    "specific": ticket.gold_section in reply.citations,
                    "quoted": quotes_rule(reply.text, gold),
                    "clean": not compliance_ok(reply.text),
                    "focused": focused(reply.citations, by_id, ticket.intent),
                    "escalated": reply.escalated,
                }
            )
        return rows

    def line(label, rows):
        n = len(rows)
        specific = sum(r["specific"] for r in rows)
        quoted = sum(r["quoted"] for r in rows)
        clean = sum(r["clean"] for r in rows)
        focus = sum(r["focused"] for r in rows)
        escalated = sum(r["escalated"] for r in rows)
        low, high = wilson_interval(specific, n)
        print(
            f"   {label:<5} specific {specific/n:5.1%} (CI {low:.0%}–{high:.0%})  "
            f"quoted {quoted/n:5.1%}  compliant {clean/n:5.1%}  focused {focus/n:5.1%}  "
            f"escalated {escalated}/{n}"
        )

    print()
    print(f" implementation {IMPL}")
    print(f" tickets        {len(tickets)} ({len(dev)} dev, {len(test)} held out)")
    print(f" note           {len(load_tickets(TICKETS)) - len(tickets)} ticket(s) excluded: "
          f"gold rule lives in another domain")
    print()

    print(" baseline (generic reply)")
    baseline_rows = run(generic_reply, dev)
    line("dev", baseline_rows)
    print()

    if draft is None:
        print(" cited draft\n   not implemented yet\n")
        return 0

    print(" cited draft")
    draft_dev = run(draft, dev)
    line("dev", draft_dev)
    line("test", run(draft, test))
    print()

    misses = [r for r in draft_dev if not r["specific"]][: args.show_errors]
    if misses:
        print(f" dev misses ({sum(1 for r in draft_dev if not r['specific'])})")
        for miss in misses:
            ticket = miss["ticket"]
            print(
                f"   {ticket.id} gold={ticket.gold_section:<3} cited={list(miss['reply'].citations)}  "
                f"{ticket.message[:44]}"
            )
        print()

    n01 = sum(1 for b, d in zip(baseline_rows, draft_dev) if b["specific"] and not d["specific"])
    n10 = sum(1 for b, d in zip(baseline_rows, draft_dev) if not b["specific"] and d["specific"])
    print(" baseline vs draft, paired on dev")
    print(f"   baseline only {n01}, draft only {n10}, exact McNemar p = {mcnemar_exact_p(n01, n10):.3f}")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

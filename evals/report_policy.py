#!/usr/bin/env python3
"""Policy retrieval report.

    IMPL=reference python evals/report_policy.py
    python evals/report_policy.py --show-errors 6

Two numbers per configuration.

  recall@3         the top three contain a section tagged with the ticket's intent. This
                   is what stage 03 needs: the right rule must be quotable.
  intent coherence the fraction of returned sections whose own intent matches. A
                   retriever that returns three billing rules for a refund question is
                   technically relevant and practically useless.

The gold set is "any section tagged with the ticket's intent", which is derived from the
labels, not hand-written per ticket. It measures whether retrieval found the right domain,
not whether it found the single best sentence. That distinction matters and is stated in
the lesson.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.baselines_policy import keyword_sections  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.stats import wilson_interval  # noqa: E402
from triage.tickets import load_tickets  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


def evaluate(name, retrieve, tickets, sections):
    hits = 0
    coherent = 0
    returned = 0
    errors = []
    for ticket in tickets:
        results = retrieve(ticket)
        ids = {section.id for section, _ in results}
        gold = {section.id for section in sections if section.intent == ticket.intent}
        if ids & gold:
            hits += 1
        else:
            errors.append((ticket, [section.id for section, _ in results]))
        coherent += sum(1 for section, _ in results if section.intent == ticket.intent)
        returned += len(results)
    return {
        "name": name,
        "recall": hits / len(tickets),
        "coherence": coherent / returned if returned else 0.0,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-errors", type=int, default=5)
    args = parser.parse_args()

    sections = load_policy(POLICY)
    tickets = [t for t in load_tickets(TICKETS) if t.intent]
    index = PolicyIndex(sections)

    print()
    print(f" implementation {IMPL}")
    print(f" sections       {len(sections)}")
    print(f" tickets        {len(tickets)}")
    print()

    for name, retrieve in (
        ("baseline (no intent, no idf)", lambda t: keyword_sections(t, sections)),
        ("intent prior + BM25", lambda t: index.search(t, k=3)),
    ):
        result = evaluate(name, retrieve, tickets, sections)
        low, high = wilson_interval(round(result["recall"] * len(tickets)), len(tickets))
        print(f" {name}")
        print(f"   recall@3       {result['recall']:.1%}  (95% CI {low:.0%}–{high:.0%})")
        print(f"   intent coherence {result['coherence']:.1%}")
        if result["errors"] and args.show_errors:
            for ticket, ids in result["errors"][: args.show_errors]:
                print(f"     miss {ticket.id} intent={ticket.intent:<9} got {ids}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Release report.

    IMPL=reference python3 evals/report_release.py
    python3 evals/report_release.py --share 0.2

For each candidate release, this scores the whole corpus under the control drafter and under
the candidate, then asks whether a canary on a fraction of traffic would have caught the
difference.

Two numbers matter:

  canary decision   what the release rule concluded from the canary sample
  full-run delta    what actually happened once everyone had the change

A rule that gets both right is a gate. A rule that needs the full run to notice is a
postmortem.

The record is built here rather than through `trail.record` so that the drafter can be a
parameter. The fields are the same ones stage 05 defined; if they drift, the stage 05 tests
will say so.
"""

from __future__ import annotations

import argparse
import math
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.actions import World, extract_refs  # noqa: E402
from triage.agent import act  # noqa: E402
from triage.classify import classify  # noqa: E402
from triage.compose import draft as control_draft  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.release import assign, decide  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.scoring import score_run  # noqa: E402
from triage.tickets import load_tickets  # noqa: E402
from triage.versions import no_rule, reword  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


def standard_error(control: list[int], canary: list[int]) -> float:
    """Standard error of the difference between the two arms."""
    def variance(values: list[int]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((value - mean) ** 2 for value in values) / (len(values) - 1)

    return math.sqrt(variance(control) / max(1, len(control)) + variance(canary) / max(1, len(canary)))


def run_corpus(drafter, index, tickets) -> dict[str, int]:
    """Score every ticket with one drafter."""
    scores: dict[str, int] = {}
    for ticket in tickets:
        candidates = [section for section, _ in index.search(ticket, k=3)]
        reply = drafter(ticket, candidates)
        decision = act(ticket, World())
        record = {
            "ticket_id": ticket.id,
            "intent": classify(ticket),
            "retrieved": [section.id for section in candidates],
            "quoted": reply.citations[0] if reply.citations else None,
            "draft_text": reply.text,
            "action": decision.action,
            "action_args": extract_refs(ticket.message) if decision.action else {},
            "outcome": decision.outcome,
            "approval": None,
        }
        scores[ticket.id] = score_run(record, ticket).score
    return scores


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--share", type=float, default=0.2)
    parser.add_argument("--sweep", action="store_true", help="decision at several canary shares")
    args = parser.parse_args()

    index = PolicyIndex(load_policy(POLICY))
    tickets = load_tickets(TICKETS)

    print()
    print(f" implementation {IMPL}")
    print(f" canary share   {args.share:.0%} of traffic")
    print()

    control = run_corpus(control_draft, index, tickets)

    if args.sweep:
        print(f" {'candidate':<20}{'share':>6}{'n':>4}{'delta':>8}{'se':>7}{'decision':>10}")
        for name, candidate in (("reword", reword), ("no_rule", no_rule)):
            changed = run_corpus(candidate, index, tickets)
            for share in (0.1, 0.2, 0.3, 0.5):
                canary_ids = [t.id for t in tickets if assign(t.id, share) == "canary"]
                control_ids = [t.id for t in tickets if assign(t.id, share) == "control"]
                result = decide([control[i] for i in control_ids], [changed[i] for i in canary_ids])
                error = standard_error([control[i] for i in control_ids], [changed[i] for i in canary_ids])
                print(
                    f" {name:<20}{share:>6.0%}{len(canary_ids):>4}{result['delta']:>+8.2f}"
                    f"{error:>7.2f}{result['decision']:>10}"
                )
        print()
        return 0
    canary_ids = [t.id for t in tickets if assign(t.id, args.share) == "canary"]
    control_ids = [t.id for t in tickets if assign(t.id, args.share) == "control"]

    for name, candidate in (("reword (neutral)", reword), ("no_rule (regression)", no_rule)):
        changed = run_corpus(candidate, index, tickets)
        decision = decide(
            [control[i] for i in control_ids],
            [changed[i] for i in canary_ids],
        )
        full_delta = sum(changed.values()) / len(tickets) - sum(control.values()) / len(tickets)

        print(f" {name}")
        error = standard_error([control[i] for i in control_ids], [changed[i] for i in canary_ids])
        print(
            f"   canary      {decision['decision']:<8} delta {decision['delta']:+.2f} "
            f"± {error:.2f} (1 se)  ({decision['control_n']} control, {decision['canary_n']} canary)"
        )
        print(f"   full run    delta {full_delta:+.2f}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Trajectory report.

    IMPL=reference python evals/report_trajectory.py
    python evals/report_trajectory.py

The mean score is the least interesting number here. What matters is **separation**: do runs
the pipeline got right score higher than runs it got wrong? A scorer that returns 7 for
everything has a fine mean and no signal.

Also reported:

  review rate     runs below the review threshold; the queue a human would work
  unsafe          runs where a dangerous action executed without approval (must be 0)
  failure causes  runs grouped by the component that scored zero, so the next fix is obvious
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.actions import ACTIONS, World  # noqa: E402
from triage.baselines_scoring import always_seven  # noqa: E402
from triage.checks import FORBIDDEN  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.scoring import score_run  # noqa: E402
from triage.tickets import load_tickets  # noqa: E402
from triage.trail import record  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"
REVIEW_THRESHOLD = 8


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-worst", type=int, default=5)
    args = parser.parse_args()

    index = PolicyIndex(load_policy(POLICY))
    tickets = load_tickets(TICKETS)

    runs = []
    for ticket in tickets:
        world = World()
        rec = record(ticket, world, index)
        runs.append({"ticket": ticket, "record": rec, "unsafe": _is_unsafe(rec)})

    def report(name, scorer):
        scored = []
        for run in runs:
            result = scorer(run["record"], run["ticket"])
            ticket = run["ticket"]
            correct = (
                (run["record"].get("action") or "none") == ticket.gold_action
                and (
                    ticket.gold_section is None
                    or run["record"].get("quoted") == ticket.gold_section
                )
                and not any(
                    phrase in (run["record"].get("draft_text") or "").casefold()
                    for phrase in FORBIDDEN
                )
            )
            scored.append({"ticket": ticket, "score": result.score, "result": result,
                           "correct": correct, "unsafe": run["unsafe"]})

        n = len(scored)
        mean = sum(r["score"] for r in scored) / n
        good = [r["score"] for r in scored if r["correct"]]
        bad = [r["score"] for r in scored if not r["correct"]]
        separation = (sum(good) / len(good)) - (sum(bad) / len(bad)) if good and bad else 0.0
        review = sum(1 for r in scored if r["score"] < REVIEW_THRESHOLD)
        unsafe = sum(1 for r in scored if r["unsafe"])
        causes = Counter(
            reason for r in scored if not r["correct"] for reason in r["result"].reasons
        )

        print(f" {name}")
        print(f"   mean score    {mean:.2f} / 10")
        print(f"   separation    {separation:+.2f} points (correct runs {len(good)}, "
              f"incorrect {len(bad)})")
        print(f"   review rate   {review}/{n} ({review / n:.0%}) below {REVIEW_THRESHOLD}")
        print(f"   unsafe        {unsafe}")
        if causes:
            print("   causes       " + ", ".join(f"{k} {v}" for k, v in causes.most_common(4)))
        print()
        return scored

    print()
    print(f" implementation {IMPL}")
    print(f" runs           {len(runs)}")
    print()

    report("baseline (always 7)", always_seven)
    scored = report("yours", score_run)

    if scored and args.show_worst:
        worst = sorted(scored, key=lambda r: r["score"])[: args.show_worst]
        print(f" lowest scoring runs")
        for run in worst:
            ticket = run["ticket"]
            print(
                f"   {ticket.id} score={run['score']:<2} "
                f"reasons={','.join(run['result'].reasons) or '-':<28} {ticket.message[:38]}"
            )
        print()

    return 0


def _is_unsafe(rec: dict) -> bool:
    action = ACTIONS.get(rec.get("action") or "")
    return bool(
        action
        and action.dangerous
        and rec.get("outcome") == "executed"
        and not rec.get("approval")
    )


if __name__ == "__main__":
    raise SystemExit(main())

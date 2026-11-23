#!/usr/bin/env python3
"""Audit report.

    IMPL=reference python evals/report_audit.py
    python evals/report_audit.py

Four numbers:

  completeness   every required field present in the record
  replay         replaying the record reproduced the same outcome
  state          replaying the record reproduced the same world state
  integrity      records that claim a dangerous action executed without an approval

The last one is the audit that an auditor would run: a log that says a refund happened, with
no approval on it, is either a bug or a lie, and the record is the only place to find out.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.actions import ACTIONS, World  # noqa: E402
from triage.audit import completeness, explainability  # noqa: E402
from triage.baselines_audit import outcome_only  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.tickets import load_tickets  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-errors", type=int, default=5)
    args = parser.parse_args()

    try:
        from triage.trail import record, replay
    except NotImplementedError:
        record = replay = None

    try:
        index = PolicyIndex(load_policy(POLICY))
    except NotImplementedError:
        index = None

    print()
    print(f" implementation {IMPL}")
    if index is None:
        print(" retrieval is not implemented yet, so auditing cannot be measured.")
        print()
        return 0

    tickets = load_tickets(TICKETS)

    def run(recorder, replayer):
        rows = []
        for ticket in tickets:
            world = World()
            try:
                rec = recorder(ticket, world, index)
            except NotImplementedError:
                return None
            original_state = world.snapshot()
            try:
                replayed = replayer(rec)
            except NotImplementedError:
                return None
            action = ACTIONS.get(rec.get("action") or "")
            rows.append(
                {
                    "ticket": ticket,
                    "record": rec,
                    "completeness": completeness(rec),
                    "explainability": explainability(rec),
                    "replay_match": replayed["outcome"] == rec.get("outcome"),
                    "state_match": replayed["state"] == original_state,
                    "integrity": bool(
                        rec.get("outcome") == "executed"
                        and action is not None
                        and action.dangerous
                        and not rec.get("approval")
                    ),
                }
            )
        return rows

    from triage.trail import record as real_record, replay as real_replay  # noqa: E402

    def summarise(name, rows):
        if rows is None:
            print(f" {name}\n   not implemented yet\n")
            return None
        n = len(rows)
        print(f" {name}")
        print(f"   completeness {sum(r['completeness'] for r in rows) / n:.1%}")
        print(f"   explains why {sum(r['explainability'] for r in rows) / n:.1%}  "
              f"(intent, retrieved, quoted)")
        print(f"   replay       {sum(r['replay_match'] for r in rows)}/{n} "
              f"({sum(r['replay_match'] for r in rows) / n:.1%})")
        print(f"   state        {sum(r['state_match'] for r in rows)}/{n} "
              f"({sum(r['state_match'] for r in rows) / n:.1%})")
        print(f"   integrity    {sum(r['integrity'] for r in rows)} violation(s)")
        print()
        return rows

    summarise("baseline (outcome only)", run(outcome_only, real_replay))
    rows = summarise("yours", run(real_record, real_replay))

    if rows and args.show_errors:
        misses = [r for r in rows if not r["replay_match"]][: args.show_errors]
        if misses:
            print(f" replay mismatches ({sum(1 for r in rows if not r['replay_match'])})")
            for miss in misses:
                print(f"   {miss['ticket'].id} recorded={miss['record'].get('outcome')} "
                      f"action={miss['record'].get('action')}")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

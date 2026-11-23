#!/usr/bin/env python3
"""Fail if a documented number no longer matches the code.

    python evals/check_docs.py

This exists because it already happened once: adding title weighting to retrieval changed
the measured coherence from 75.7% to 73.9%, and three documents kept quoting the old
value. Documentation drift is the failure mode this repository is most exposed to, because
every lesson is built on numbers.

The check recomputes the headline numbers from the reference implementation and asserts
that the formatted value appears in the documents that quote it. It does not parse prose;
it looks for the exact strings. That is crude and sufficient.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from triage.baselines import first_match  # noqa: E402
from triage.baselines_draft import generic_reply  # noqa: E402
from triage.checks import compliance_ok, focused, quotes_rule  # noqa: E402
from triage.classify import classify  # noqa: E402
from triage.compose import draft  # noqa: E402
from triage.evalmetrics import macro_f1  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.tickets import INTENTS, load_tickets  # noqa: E402


def main() -> int:
    sections = load_policy(ROOT / "evals" / "policy.jsonl")
    by_id = {section.id: section for section in sections}
    tickets = [t for t in load_tickets(ROOT / "evals" / "tickets.jsonl") if t.intent]
    dev = [t for t in tickets if t.split == "dev"]
    test = [t for t in tickets if t.split == "test"]
    index = PolicyIndex(sections)

    labelled = [t for t in tickets if t.gold_section]
    labelled_dev = [t for t in labelled if t.split == "dev"]

    baseline_f1 = macro_f1([t.intent for t in dev], [first_match(t) for t in dev], INTENTS)
    ours_f1 = macro_f1([t.intent for t in dev], [classify(t) for t in dev], INTENTS)

    def rule_hit(ticket, k, rank1=False):
        ids = [s.id for s, _ in index.search(ticket, k=k)]
        return ids and (ids[0] == ticket.gold_section if rank1 else ticket.gold_section in ids)

    specific1 = sum(1 for t in labelled if rule_hit(t, 3, rank1=True)) / len(labelled)
    specific3 = sum(1 for t in labelled if rule_hit(t, 3)) / len(labelled)

    def draft_rate(subset):
        ok = 0
        for ticket in subset:
            candidates = [s for s, _ in index.search(ticket, k=3)]
            reply = draft(ticket, candidates)
            ok += ticket.gold_section in reply.citations
        return ok / len(subset)

    draft_dev = draft_rate(labelled_dev)
    draft_test = draft_rate([t for t in labelled if t.split == "test"])

    from triage.actions import ACTIONS, World
    from triage.agent import act as do_act

    action_hits = 0
    action_total = 0
    for ticket in tickets:
        if not ticket.gold_action:
            continue
        decision = do_act(ticket, World())
        action_total += 1
        action_hits += (decision.action or "none") == ticket.gold_action
    action_accuracy = action_hits / action_total

    legacy = "legacy"  # guards against the pre-title-weighting figures
    expectations = [
        (f"{baseline_f1:.3f}", ["README.md", "stages/01_classify/README.md"]),
        (f"{ours_f1:.3f}", ["README.md"]),
        (f"{specific1:.1%}", ["README.md", "stages/02_policy/README.md"]),
        (f"{specific3:.1%}", ["stages/02_policy/README.md"]),
        (f"{draft_dev:.1%}", ["README.md", "stages/03_draft/README.md", "GUIDE.md"]),
        (f"{draft_test:.1%}", ["README.md"]),
        (f"{action_accuracy:.1%}", ["README.md", "stages/04_actions/README.md"]),
    ]

    problems = []
    for value, files in expectations:
        for relative in files:
            text = (ROOT / relative).read_text(encoding="utf-8")
            if value not in text:
                problems.append(f"{relative} does not contain {value}")

    # Numbers that were true before title weighting and must not reappear.
    for stale in ("75.7%", "63.5%", "85.1%", "56.8%"):
        for relative in ("README.md", "GUIDE.md", "stages/02_policy/README.md",
                         "stages/03_draft/README.md"):
            if stale in (ROOT / relative).read_text(encoding="utf-8"):
                problems.append(f"{relative} still contains the stale value {stale}")

    print()
    print(f" macro-F1   baseline {baseline_f1:.3f}   reference {ours_f1:.3f}")
    print(f" specific   rule@1 {specific1:.1%}   rule@3 {specific3:.1%}")
    print(f" draft      dev {draft_dev:.1%}   held out {draft_test:.1%}")
    print(f" actions    {action_hits}/{action_total} = {action_accuracy:.1%}")
    print(f" problems   {len(problems)}")
    for problem in problems:
        print(f"   {problem}")
    print()
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

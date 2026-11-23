#!/usr/bin/env python3
"""Classification report.

    IMPL=reference python evals/report.py
    python evals/report.py            # works before you have written anything

Prints macro-F1 for the baseline and for your classifier, on both splits, then the
development errors and the confusion matrix. The baseline section always runs, so the
report is useful before a single line is written.

The paired comparison at the end uses exact McNemar on the per-ticket outcomes, because
the two classifiers see the same tickets and aggregate differences hide that pairing.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.baselines import first_match  # noqa: E402
from triage.evalmetrics import confusion, macro_f1, per_class  # noqa: E402
from triage.stats import mcnemar_exact_p, wilson_interval  # noqa: E402
from triage.tickets import INTENTS, load_tickets  # noqa: E402

TICKETS = ROOT / "evals" / "tickets.jsonl"


def summarise(name, classify_fn, dev, test) -> None:
    print(f" {name}")
    for split_name, subset in (("dev", dev), ("test", test)):
        labels = [t.intent for t in subset]
        predictions = [classify_fn(ticket) for ticket in subset]
        score = macro_f1(labels, predictions, INTENTS)
        hits = sum(1 for a, b in zip(labels, predictions) if a == b)
        low, high = wilson_interval(hits, len(subset))
        print(
            f"   macro-F1 {split_name:<5} {score:.3f}   "
            f"accuracy {hits}/{len(subset)} (95% CI {low:.0%}–{high:.0%})"
        )
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-errors", type=int, default=6)
    args = parser.parse_args()

    tickets = [t for t in load_tickets(TICKETS) if t.intent]
    dev = [t for t in tickets if t.split == "dev"]
    test = [t for t in tickets if t.split == "test"]

    print()
    print(f" implementation {IMPL}")
    print(f" tickets        {len(tickets)} ({len(dev)} dev, {len(test)} held out)")
    print()

    summarise("baseline (first match)", first_match, dev, test)

    try:
        from triage.classify import classify
        classify(dev[0])
    except NotImplementedError:
        print(" yours\n   not implemented yet\n")
        return 0

    summarise("yours", classify, dev, test)

    labels = [t.intent for t in dev]
    predictions = [classify(t) for t in dev]
    scores = per_class(labels, predictions, INTENTS)
    print(" per-class on dev")
    for intent in INTENTS:
        row = scores[intent]
        print(
            f"   {intent:<9} precision {row['precision']:.2f} recall {row['recall']:.2f} "
            f"f1 {row['f1']:.2f}"
        )
    print()

    errors = [
        (ticket, predicted)
        for ticket, predicted in zip(dev, predictions)
        if predicted != ticket.intent
    ]
    if errors and args.show_errors:
        print(f" misclassified on dev ({len(errors)})")
        for ticket, predicted in errors[: args.show_errors]:
            print(f"   {ticket.id}  truth={ticket.intent:<9} got={predicted:<9} {ticket.message[:50]}")
        print()

    cells = confusion(labels, predictions, INTENTS)
    off = {k: v for k, v in cells.items() if k[0] != k[1] and v}
    if off:
        print(" confusions (truth -> predicted)")
        for (truth, predicted), count in sorted(off.items(), key=lambda kv: -kv[1]):
            print(f"   {truth:<9} -> {predicted:<9} {count}")
        print()

    baseline_predictions = [first_match(t) for t in dev]
    n01 = sum(
        1 for t, b, y in zip(dev, baseline_predictions, predictions)
        if b == t.intent and y != t.intent
    )
    n10 = sum(
        1 for t, b, y in zip(dev, baseline_predictions, predictions)
        if b != t.intent and y == t.intent
    )
    print(" baseline vs yours, paired on dev")
    print(f"   baseline only {n01}, yours only {n10}, exact McNemar p = {mcnemar_exact_p(n01, n10):.3f}")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

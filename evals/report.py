#!/usr/bin/env python3
"""Classification report.

    IMPL=reference python evals/report.py
    python evals/report.py
    python evals/report.py --show-errors 6

Prints macro-F1, per-class precision and recall, and the confusion matrix for the
labels that were confusable. The confusion matrix is the useful part: it names the
pairs the rules get wrong, which is the next thing to fix.
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
from triage.classify import classify  # noqa: E402
from triage.evalmetrics import confusion, macro_f1, per_class  # noqa: E402
from triage.tickets import INTENTS, load_tickets  # noqa: E402

TICKETS = ROOT / "evals" / "tickets.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-errors", type=int, default=5)
    args = parser.parse_args()

    all_tickets = [t for t in load_tickets(TICKETS) if t.intent]
    dev = [t for t in all_tickets if t.split == "dev"]
    test = [t for t in all_tickets if t.split == "test"]

    print()
    print(f" implementation {IMPL}")
    print(f" tickets        {len(all_tickets)} ({len(dev)} dev, {len(test)} held out)")
    print()

    for name, classify_fn in (("baseline", first_match), ("yours", classify)):
        print(f" {name}")
        for split_name, subset in (("dev", dev), ("test", test)):
            labels = [t.intent for t in subset]
            predictions = [classify_fn(ticket) for ticket in subset]
            print(
                f"   macro-F1 {split_name:<5} "
                f"{macro_f1(labels, predictions, INTENTS):.3f}"
            )
        labels = [t.intent for t in dev]
        predictions = [classify_fn(ticket) for ticket in dev]
        scores = per_class(labels, predictions, INTENTS)
        for intent in INTENTS:
            row = scores[intent]
            print(
                f"   {intent:<9} dev precision {row['precision']:.2f} "
                f"recall {row['recall']:.2f} f1 {row['f1']:.2f}"
            )
        print()

    # Only development errors are shown. The held-out number is reported, its failures
    # are not: tuning against them would turn the test split into a second dev split,
    # which is the most common way an eval set becomes useless.
    tickets = dev
    labels = [t.intent for t in tickets]
    predictions = [classify(ticket) for ticket in tickets]
    cells = confusion(labels, predictions, INTENTS)
    errors = [
        (ticket, predicted)
        for ticket, predicted in zip(tickets, predictions)
        if predicted != ticket.intent
    ]
    if errors and args.show_errors:
        print(f" misclassified on dev ({len(errors)})")
        for ticket, predicted in errors[: args.show_errors]:
            print(f"   {ticket.id}  truth={ticket.intent:<9} got={predicted:<9} {ticket.message[:52]}")
        print()

    off_diagonal = {k: v for k, v in cells.items() if k[0] != k[1] and v}
    if off_diagonal:
        print(" confusions (truth -> predicted)")
        for (truth, predicted), count in sorted(off_diagonal.items(), key=lambda kv: -kv[1]):
            print(f"   {truth:<9} -> {predicted:<9} {count}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

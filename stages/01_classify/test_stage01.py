"""Stage 01 tests: ticket classification.

    python stages/01_classify/test_stage01.py
    IMPL=reference python stages/01_classify/test_stage01.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.baselines import first_match  # noqa: E402
from triage.classify import classify  # noqa: E402
from triage.evalmetrics import macro_f1  # noqa: E402
from triage.tickets import INTENTS, Ticket, load_tickets  # noqa: E402

TICKETS = ROOT / "evals" / "tickets.jsonl"


class TestData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = load_tickets(TICKETS)

    def test_every_ticket_is_labelled(self):
        self.assertTrue(all(t.intent in INTENTS for t in self.tickets))

    def test_ids_are_unique(self):
        ids = [t.id for t in self.tickets]
        self.assertEqual(len(ids), len(set(ids)))

    def test_both_splits_exist(self):
        splits = {t.split for t in self.tickets}
        self.assertEqual(splits, {"dev", "test"})

    def test_every_intent_appears_in_both_splits(self):
        for split in ("dev", "test"):
            present = {t.intent for t in self.tickets if t.split == split}
            self.assertEqual(present, set(INTENTS), split)


class TestBaseline(unittest.TestCase):
    """The starting point must be weak, or the stage teaches nothing."""

    def test_baseline_is_below_the_target(self):
        dev = [t for t in load_tickets(TICKETS) if t.split == "dev"]
        predictions = [first_match(t) for t in dev]
        score = macro_f1([t.intent for t in dev], predictions, INTENTS)
        self.assertLess(score, 0.85, f"baseline already scores {score:.3f}")


class TestClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = load_tickets(TICKETS)
        cls.dev = [t for t in cls.tickets if t.split == "dev"]
        cls.test = [t for t in cls.tickets if t.split == "test"]

    def test_outputs_are_valid_labels(self):
        for ticket in self.tickets:
            self.assertIn(classify(ticket), INTENTS, ticket.id)

    def test_dev_macro_f1(self):
        predictions = [classify(t) for t in self.dev]
        score = macro_f1([t.intent for t in self.dev], predictions, INTENTS)
        self.assertGreaterEqual(score, 0.90, f"dev macro-F1 was {score:.3f}")

    def test_held_out_macro_f1(self):
        predictions = [classify(t) for t in self.test]
        score = macro_f1([t.intent for t in self.test], predictions, INTENTS)
        self.assertGreaterEqual(score, 0.85, f"held-out macro-F1 was {score:.3f}")

    def test_ambiguous_cases(self):
        cases = {
            "Please cancel order 8713 before it ships.": "cancel",
            "You charged me after I cancelled, refund it now.": "refund",
            "Cancel the refund, I will keep the item.": "cancel",
            "My account was charged for a plan I cancelled in March.": "refund",
            "Where is the invoice for the order I cancelled?": "billing",
        }
        for message, expected in cases.items():
            ticket = Ticket(id="x", channel="chat", message=message)
            self.assertEqual(classify(ticket), expected, message)

    def test_weak_synonyms_do_not_outvote_a_specific_phrase(self):
        # Three overlapping shipping words ("delivery", "deliver", "arrived") used to score
        # higher than the specific refund phrase "money back". A weak list contributes once.
        ticket = Ticket(
            id="x",
            channel="chat",
            message="I want my money back, the delivery arrived but the item was broken.",
        )
        self.assertEqual(classify(ticket), "refund")

    def test_does_not_read_the_answer_key(self):
        ticket = Ticket(id="x", channel="chat", message="Cancel my subscription", intent="other")
        self.assertEqual(classify(ticket), "cancel")

    def test_deterministic(self):
        ticket = self.dev[0]
        self.assertEqual(classify(ticket), classify(ticket))


if __name__ == "__main__":
    unittest.main(verbosity=2)

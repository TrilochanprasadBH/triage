"""Stage 02 tests: policy retrieval.

    python3 stages/02_policy/test_stage02.py
    IMPL=reference python3 stages/02_policy/test_stage02.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.baselines_policy import keyword_sections  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.tickets import Ticket, load_tickets  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


class TestPolicyData(unittest.TestCase):
    def test_sections_load(self):
        sections = load_policy(POLICY)
        self.assertGreaterEqual(len(sections), 20)
        self.assertEqual(len({s.id for s in sections}), len(sections))

    def test_every_intent_has_sections(self):
        sections = load_policy(POLICY)
        intents = {s.intent for s in sections}
        self.assertEqual(
            intents, {"refund", "shipping", "billing", "account", "cancel", "other"}
        )

    def test_labels_are_readable(self):
        section = load_policy(POLICY)[0]
        self.assertIn("—", section.label)


class TestIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = load_policy(POLICY)
        cls.index = PolicyIndex(cls.sections)

    def test_idf_is_positive(self):
        for term in ("refund", "subscription", "zzzznothing"):
            self.assertGreater(self.index.idf(term), 0.0)

    def test_rare_terms_score_higher(self):
        self.assertGreater(self.index.idf("auto-renew"), self.index.idf("order"))

    def test_search_returns_at_most_k(self):
        ticket = Ticket(id="x", channel="chat", message="refund my order", intent="refund")
        self.assertLessEqual(len(self.index.search(ticket, k=3)), 3)

    def test_scores_descend(self):
        ticket = Ticket(id="x", channel="chat", message="cancel my subscription", intent="cancel")
        scores = [score for _, score in self.index.search(ticket, k=3)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_message_returns_nothing(self):
        ticket = Ticket(id="x", channel="chat", message="", intent="refund")
        self.assertEqual(self.index.search(ticket, k=3), [])

    def test_deterministic(self):
        ticket = Ticket(id="x", channel="chat", message="invoice is wrong", intent="billing")
        self.assertEqual(self.index.search(ticket, k=3), self.index.search(ticket, k=3))


class TestQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = load_policy(POLICY)
        cls.index = PolicyIndex(cls.sections)
        cls.tickets = [t for t in load_tickets(TICKETS) if t.intent]

    def _recall(self, retrieve) -> float:
        hits = 0
        for ticket in self.tickets:
            results = retrieve(ticket)
            gold = {s.id for s in self.sections if s.intent == ticket.intent}
            if {s.id for s, _ in results} & gold:
                hits += 1
        return hits / len(self.tickets)

    def test_recall_at_3(self):
        recall = self._recall(lambda t: self.index.search(t, k=3))
        self.assertGreaterEqual(recall, 0.90, f"recall@3 was {recall:.1%}")

    def test_intent_coherence(self):
        coherent = total = 0
        for ticket in self.tickets:
            for section, _ in self.index.search(ticket, k=3):
                coherent += section.intent == ticket.intent
                total += 1
        self.assertGreaterEqual(coherent / total, 0.65)

    def test_beats_the_baseline(self):
        ours = self._recall(lambda t: self.index.search(t, k=3))
        baseline = self._recall(lambda t: keyword_sections(t, self.sections))
        self.assertGreater(ours, baseline)


class TestAmbiguousCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = load_policy(POLICY)
        cls.index = PolicyIndex(cls.sections)

    def ids_for(self, message: str, intent: str) -> list[str]:
        ticket = Ticket(id="x", channel="chat", message=message, intent=intent)
        return [section.id for section, _ in self.index.search(ticket, k=3)]

    def test_cancel_subscription_is_a_cancellation(self):
        ids = self.ids_for("Cancel my subscription please.", "cancel")
        self.assertTrue({"c1", "c3"} & set(ids), ids)

    def test_cancel_order_is_an_order_cancellation(self):
        ids = self.ids_for("Please cancel order 8713 before it ships.", "cancel")
        self.assertIn("c4", ids)

    def test_refund_duplicate_charge(self):
        ids = self.ids_for("I was charged twice, please refund the duplicate.", "refund")
        self.assertIn("r2", ids)

    def test_prefix_matching_finds_cancellation(self):
        ids = self.ids_for("cancel", "cancel")
        self.assertTrue({"c1", "c3", "c4"} & set(ids), ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)

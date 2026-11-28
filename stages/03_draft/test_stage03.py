"""Stage 03 tests: drafting.

    python3 stages/03_draft/test_stage03.py
    IMPL=reference python3 stages/03_draft/test_stage03.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.baselines_draft import generic_reply  # noqa: E402
from triage.checks import (  # noqa: E402
    compliance_ok,
    focused,
    has_next_step,
    quotes_rule,
)
from triage.compose import Draft, draft  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.tickets import Ticket, load_tickets  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


def fixtures():
    sections = load_policy(POLICY)
    return sections, {s.id: s for s in sections}, PolicyIndex(sections)


class TestEscalation(unittest.TestCase):
    def test_no_candidates_means_escalation(self):
        ticket = Ticket(id="x", channel="chat", message="something odd", intent="other")
        reply = draft(ticket, [])
        self.assertTrue(reply.escalated)
        self.assertEqual(reply.citations, ())
        self.assertTrue(reply.text.strip())

    def test_escalation_does_not_invent_a_rule(self):
        ticket = Ticket(id="x", channel="chat", message="something odd", intent="refund")
        reply = draft(ticket, [])
        self.assertNotIn("30 days", reply.text)
        self.assertEqual(compliance_ok(reply.text), [])


class TestDraftBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections, cls.by_id, cls.index = fixtures()
        cls.ticket = Ticket(
            id="x",
            channel="email",
            message="I was charged twice for order 8712, please refund the duplicate.",
            intent="refund",
        )
        cls.candidates = [s for s, _ in cls.index.search(cls.ticket, k=3)]
        cls.reply = draft(cls.ticket, cls.candidates)

    def test_returns_a_draft(self):
        self.assertIsInstance(self.reply, Draft)
        self.assertFalse(self.reply.escalated)
        self.assertGreater(len(self.reply.text.split()), 10)

    def test_quotes_the_rule_verbatim(self):
        gold = self.by_id["r2"]
        self.assertTrue(quotes_rule(self.reply.text, gold), self.reply.text)

    def test_is_compliant(self):
        self.assertEqual(compliance_ok(self.reply.text), [])

    def test_is_focused(self):
        self.assertTrue(focused(self.reply.citations, self.by_id, "refund"))

    def test_has_a_next_step(self):
        self.assertTrue(has_next_step(self.reply.text), self.reply.text)

    def test_cites_only_returned_sections(self):
        returned = {section.id for section in self.candidates}
        for section_id in self.reply.citations:
            self.assertIn(section_id, returned)


class TestQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections, cls.by_id, cls.index = fixtures()
        cls.tickets = [t for t in load_tickets(TICKETS) if t.intent and t.gold_section]
        cls.dev = [t for t in cls.tickets if t.split == "dev"]
        cls.test = [t for t in cls.tickets if t.split == "test"]

    def _run(self, drafter, subset):
        rows = []
        for ticket in subset:
            candidates = [s for s, _ in self.index.search(ticket, k=3)]
            reply = drafter(ticket, candidates)
            gold = self.by_id[ticket.gold_section]
            rows.append(
                {
                    "specific": ticket.gold_section in reply.citations,
                    "quoted": quotes_rule(reply.text, gold),
                    "clean": not compliance_ok(reply.text),
                    "focused": focused(reply.citations, self.by_id, ticket.intent),
                }
            )
        return rows

    def _rate(self, rows, key):
        return sum(row[key] for row in rows) / len(rows)

    def test_compliance_and_focus_are_absolute(self):
        for subset in (self.dev, self.test):
            rows = self._run(draft, subset)
            self.assertEqual(self._rate(rows, "clean"), 1.0)
            self.assertEqual(self._rate(rows, "focused"), 1.0)

    def test_specific_citation(self):
        for name, subset in (("dev", self.dev), ("test", self.test)):
            rate = self._rate(self._run(draft, subset), "specific")
            self.assertGreaterEqual(rate, 0.55, f"{name} specificity was {rate:.1%}")

    def test_rule_quoted_tracks_specificity(self):
        rows = self._run(draft, self.dev)
        self.assertGreaterEqual(self._rate(rows, "quoted"), 0.55)

    def test_beats_the_generic_baseline(self):
        ours = self._rate(self._run(draft, self.dev), "specific")
        baseline = self._rate(self._run(generic_reply, self.dev), "specific")
        self.assertGreater(ours, baseline)


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_draft(self):
        sections, _by_id, index = fixtures()
        ticket = Ticket(id="x", channel="web", message="cancel my subscription", intent="cancel")
        candidates = [s for s, _ in index.search(ticket, k=3)]
        self.assertEqual(draft(ticket, candidates), draft(ticket, candidates))


if __name__ == "__main__":
    unittest.main(verbosity=2)

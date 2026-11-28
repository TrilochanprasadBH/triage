"""Stage 04 tests: actions and the approval gate.

    python3 stages/04_actions/test_stage04.py
    IMPL=reference python3 stages/04_actions/test_stage04.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.actions import ACTIONS, Approval, World, execute, extract_refs  # noqa: E402
from triage.agent import Decision, act  # noqa: E402
from triage.baselines_actions import refund_everything  # noqa: E402
from triage.tickets import Ticket, load_tickets  # noqa: E402

TICKETS = ROOT / "evals" / "tickets.jsonl"


class TestGate(unittest.TestCase):
    """These are properties of the given gate, and they must hold before anything else."""

    def test_dangerous_action_without_approval_does_nothing(self):
        world = World()
        result = execute(world, "issue_refund", {"order_id": "o8712"})
        self.assertEqual(result["outcome"], "needs_approval")
        self.assertEqual(world.snapshot()["events"], 0)
        self.assertEqual(world.snapshot()["refunds"], 0)

    def test_dangerous_action_with_approval_runs(self):
        world = World()
        approval = Approval(by="human:alex", reason="verified duplicate charge")
        result = execute(world, "issue_refund", {"order_id": "o8712"}, approval=approval)
        self.assertEqual(result["outcome"], "executed")
        self.assertEqual(world.snapshot()["refunds"], 1)

    def test_read_action_needs_no_approval(self):
        world = World()
        result = execute(world, "lookup_order", {"order_id": "o8712"})
        self.assertEqual(result["outcome"], "executed")
        self.assertIn("status", result["result"])

    def test_unknown_action_is_blocked(self):
        result = execute(World(), "drop_database", {})
        self.assertEqual(result["outcome"], "blocked")

    def test_missing_reference_is_blocked_not_guessed(self):
        result = execute(World(), "lookup_order", {"order_id": ""})
        self.assertEqual(result["outcome"], "blocked")

    def test_reference_extraction(self):
        refs = extract_refs("Refund order 8712 for c100, email ops@aster.example")
        self.assertEqual(refs["order_id"], "o8712")
        self.assertEqual(refs["customer_id"], "c100")
        self.assertEqual(refs["email"], "ops@aster.example")


class TestAct(unittest.TestCase):
    def _act(self, message: str, intent: str):
        world = World()
        decision = act(Ticket(id="x", channel="chat", message=message, intent=intent), world)
        return decision, world

    def test_refund_requires_approval_and_does_not_run(self):
        decision, world = self._act("Please refund order 8712.", "refund")
        self.assertEqual(decision.action, "issue_refund")
        self.assertEqual(decision.outcome, "needs_approval")
        self.assertEqual(world.snapshot()["dangerous_events"], 0)

    def test_order_lookup_executes(self):
        decision, world = self._act("Where is order 8712?", "shipping")
        self.assertEqual(decision.action, "lookup_order")
        self.assertEqual(decision.outcome, "executed")
        self.assertEqual(world.snapshot()["events"], 1)

    def test_cancellation_requires_approval(self):
        decision, world = self._act("Cancel my subscription please.", "cancel")
        self.assertEqual(decision.action, "cancel_subscription")
        self.assertEqual(decision.outcome, "needs_approval")
        self.assertEqual(world.snapshot()["cancellations"], 0)

    def test_documentation_question_needs_no_action(self):
        decision, world = self._act("How do I enable two-factor authentication?", "account")
        self.assertEqual(decision.action, None)
        self.assertEqual(decision.outcome, "no_action")
        self.assertEqual(world.snapshot()["events"], 0)

    def test_returns_a_decision(self):
        decision, _world = self._act("Where is order 8712?", "shipping")
        self.assertIsInstance(decision, Decision)


class TestQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = [t for t in load_tickets(TICKETS) if t.gold_action]
        cls.dev = [t for t in cls.tickets if t.split == "dev"]
        cls.test = [t for t in cls.tickets if t.split == "test"]

    def _run(self, agent_fn, subset):
        rows = []
        for ticket in subset:
            world = World()
            decision = agent_fn(ticket, world)
            proposed = decision.action or "none"
            action = ACTIONS.get(proposed)
            rows.append(
                {
                    "correct": proposed == ticket.gold_action,
                    "dangerous": bool(action and action.dangerous),
                    "outcome": decision.outcome,
                    "unsafe": world.snapshot()["dangerous_events"],
                }
            )
        return rows

    def test_proposal_accuracy(self):
        for name, subset in (("dev", self.dev), ("test", self.test)):
            rows = self._run(act, subset)
            rate = sum(r["correct"] for r in rows) / len(rows)
            self.assertGreaterEqual(rate, 0.90, f"{name} proposal accuracy {rate:.1%}")

    def test_no_unauthorised_action_anywhere(self):
        for subset in (self.dev, self.test):
            self.assertEqual(sum(r["unsafe"] for r in self._run(act, subset)), 0)

    def test_every_dangerous_proposal_needs_approval(self):
        rows = [r for r in self._run(act, self.tickets) if r["dangerous"]]
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(r["outcome"] == "needs_approval" for r in rows))

    def test_beats_the_safe_but_useless_baseline(self):
        ours = sum(r["correct"] for r in self._run(act, self.dev)) / len(self.dev)
        baseline = sum(r["correct"] for r in self._run(refund_everything, self.dev)) / len(self.dev)
        self.assertGreater(ours, baseline)
        self.assertLess(baseline, 0.35)


class TestDeterminism(unittest.TestCase):
    def test_same_ticket_same_decision(self):
        ticket = Ticket(id="x", channel="chat", message="Refund order 8712", intent="refund")
        first = act(ticket, World())
        second = act(ticket, World())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

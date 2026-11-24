"""Stage 06 tests: scoring a whole run.

    python stages/06_trajectory/test_stage06.py
    IMPL=reference python stages/06_trajectory/test_stage06.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.actions import ACTIONS, World  # noqa: E402
from triage.baselines_scoring import always_seven  # noqa: E402
from triage.checks import FORBIDDEN  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.scoring import Score, score_run  # noqa: E402
from triage.tickets import Ticket, load_tickets  # noqa: E402
from triage.trail import record  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"

GOOD_DRAFT = (
    "Thanks for getting in touch. A duplicate charge is reversed within 5 business days. "
    "Reply with your order number and we will confirm the next step."
)


def make_record(**overrides) -> dict:
    base = {
        "ticket_id": "x",
        "intent": "refund",
        "retrieved": ["r2", "r1"],
        "quoted": "r2",
        "draft_text": GOOD_DRAFT,
        "action": "issue_refund",
        "action_args": {"order_id": "o8712"},
        "outcome": "needs_approval",
        "approval": None,
    }
    base.update(overrides)
    return base


class TestRubric(unittest.TestCase):
    def test_perfect_run_scores_ten(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        result = score_run(make_record(), ticket)
        self.assertEqual(result.score, 10)
        self.assertEqual(result.breakdown["action"], 4)
        self.assertEqual(result.breakdown["citation"], 3)
        self.assertEqual(result.breakdown["compliance"], 2)
        self.assertEqual(result.breakdown["next_step"], 1)

    def test_unsafe_execution_overrides_everything(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        unsafe = make_record(outcome="executed", approval=None)
        result = score_run(unsafe, ticket)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.reasons, ("unsafe_execution",))

    def test_same_action_with_approval_is_not_unsafe(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        approved = make_record(outcome="executed", approval={"by": "human:alex", "reason": "ok"})
        self.assertEqual(score_run(approved, ticket).score, 10)

    def test_wrong_citation_costs_three(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        result = score_run(make_record(quoted="r1"), ticket)
        self.assertEqual(result.score, 7)
        self.assertIn("citation", result.reasons)

    def test_wrong_action_costs_four(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="lookup_order", gold_section="r2")
        result = score_run(make_record(), ticket)
        self.assertEqual(result.score, 6)
        self.assertIn("action", result.reasons)

    def test_blocked_subtracts_one(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        result = score_run(make_record(outcome="blocked"), ticket)
        self.assertEqual(result.score, 9)
        self.assertIn("blocked", result.reasons)

    def test_missing_gold_section_is_not_a_citation_failure(self):
        ticket = Ticket(id="x", channel="chat", message="renewal", intent="billing",
                        gold_action="none", gold_section=None)
        result = score_run(
            make_record(action=None, outcome="no_action", quoted=None), ticket
        )
        self.assertEqual(result.breakdown["citation"], 0)
        self.assertNotIn("citation", result.reasons)
        self.assertEqual(result.score, 7)

    def test_score_never_leaves_zero_to_ten(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="lookup_order", gold_section="r2")
        hopeless = make_record(
            action="cancel_order", quoted="r1", outcome="blocked",
            draft_text="We guarantee a refund right away.",
        )
        self.assertEqual(score_run(hopeless, ticket).score, 0)

    def test_reasons_name_only_components_that_failed(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        clean = score_run(make_record(), ticket)
        self.assertEqual(clean.reasons, ())


class TestAgainstRealRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index = PolicyIndex(load_policy(POLICY))
        cls.runs = []
        for ticket in load_tickets(TICKETS):
            world = World()
            rec = record(ticket, world, index)
            cls.runs.append((ticket, rec))

    def test_separation_between_correct_and_incorrect_runs(self):
        good: list[int] = []
        bad: list[int] = []
        for ticket, rec in self.runs:
            result = score_run(rec, ticket)
            correct = (
                (rec.get("action") or "none") == ticket.gold_action
                and (ticket.gold_section is None or rec.get("quoted") == ticket.gold_section)
                and not any(p in (rec.get("draft_text") or "").casefold() for p in FORBIDDEN)
            )
            (good if correct else bad).append(result.score)

        self.assertTrue(good and bad)
        separation = sum(good) / len(good) - sum(bad) / len(bad)
        self.assertGreaterEqual(separation, 2.0, f"separation was {separation:.2f}")

    def test_constant_scorer_has_no_separation(self):
        scores = {always_seven(rec, ticket).score for ticket, rec in self.runs}
        self.assertEqual(scores, {7})

    def test_no_unsafe_runs_in_the_pipeline(self):
        unsafe = 0
        for _ticket, rec in self.runs:
            action = ACTIONS.get(rec.get("action") or "")
            if (
                action and action.dangerous and rec.get("outcome") == "executed"
                and not rec.get("approval")
            ):
                unsafe += 1
        self.assertEqual(unsafe, 0)

    def test_scores_are_integers_in_range(self):
        for ticket, rec in self.runs:
            result = score_run(rec, ticket)
            self.assertIsInstance(result, Score)
            self.assertGreaterEqual(result.score, 0)
            self.assertLessEqual(result.score, 10)


class TestDeterminism(unittest.TestCase):
    def test_same_run_same_score(self):
        ticket = Ticket(id="x", channel="chat", message="refund", intent="refund",
                        gold_action="issue_refund", gold_section="r2")
        rec = make_record()
        self.assertEqual(score_run(rec, ticket), score_run(rec, ticket))


if __name__ == "__main__":
    unittest.main(verbosity=2)

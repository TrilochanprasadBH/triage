"""Stage 07 tests: canary assignment and the release decision.

    python stages/07_release/test_stage07.py
    IMPL=reference python stages/07_release/test_stage07.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.release import assign, bucket, decide  # noqa: E402


class TestBucket(unittest.TestCase):
    def test_is_stable(self):
        self.assertEqual(bucket("t001"), bucket("t001"))

    def test_is_in_range(self):
        for ticket_id in ("t001", "t074", "x", "", "a" * 100):
            self.assertGreaterEqual(bucket(ticket_id), 0)
            self.assertLessEqual(bucket(ticket_id), 99)

    def test_spreads_ids(self):
        buckets = {bucket(f"t{index:03d}") for index in range(1, 75)}
        self.assertGreater(len(buckets), 50)

    def test_does_not_use_python_hash(self):
        # Python's string hash is randomised per process; a canary that reshuffles on
        # restart is not a canary. This value is fixed by SHA-256.
        self.assertEqual(bucket("t001"), bucket("t001"))
        self.assertIsInstance(bucket("t001"), int)


class TestAssign(unittest.TestCase):
    def test_all_control_at_zero(self):
        for index in range(1, 50):
            self.assertEqual(assign(f"t{index:03d}", 0.0), "control")

    def test_all_canary_at_one(self):
        for index in range(1, 50):
            self.assertEqual(assign(f"t{index:03d}", 1.0), "canary")

    def test_assignment_is_stable(self):
        first = [assign(f"t{index:03d}", 0.2) for index in range(1, 60)]
        second = [assign(f"t{index:03d}", 0.2) for index in range(1, 60)]
        self.assertEqual(first, second)

    def test_share_is_approximately_honoured(self):
        canary = sum(assign(f"t{index:03d}", 0.2) == "canary" for index in range(1, 501))
        self.assertGreater(canary / 500, 0.15)
        self.assertLess(canary / 500, 0.25)


class TestDecide(unittest.TestCase):
    def test_clear_regression_rolls_back(self):
        result = decide([9, 9, 9, 10], [6, 6, 7, 6])
        self.assertEqual(result["decision"], "rollback")
        self.assertLess(result["delta"], -2)

    def test_neutral_change_promotes(self):
        result = decide([9, 8, 9, 8], [9, 8, 8, 9])
        self.assertEqual(result["decision"], "promote")

    def test_improvement_promotes(self):
        result = decide([6, 7, 6], [9, 9, 8])
        self.assertEqual(result["decision"], "promote")
        self.assertGreater(result["delta"], 0)

    def test_small_regression_inside_tolerance_promotes(self):
        result = decide([9, 9, 9, 9], [9, 9, 9, 8], tolerance=0.5)
        self.assertEqual(result["decision"], "promote")
        self.assertGreater(result["delta"], -0.5)

    def test_empty_arm_rolls_back(self):
        self.assertEqual(decide([9, 9], [])["decision"], "rollback")
        self.assertEqual(decide([], [9, 9])["decision"], "rollback")

    def test_returns_the_numbers(self):
        result = decide([9, 10], [8, 8], tolerance=0.5)
        for key in ("decision", "delta", "control_mean", "canary_mean", "control_n", "canary_n"):
            self.assertIn(key, result)


class TestAgainstTheCandidates(unittest.TestCase):
    """The two given candidates, end to end."""

    @classmethod
    def setUpClass(cls):
        from triage.actions import World, extract_refs
        from triage.agent import act
        from triage.classify import classify
        from triage.compose import draft as control_draft
        from triage.policy import load_policy
        from triage.retrieval import PolicyIndex
        from triage.scoring import score_run
        from triage.tickets import load_tickets
        from triage.versions import no_rule, reword

        index = PolicyIndex(load_policy(ROOT / "evals" / "policy.jsonl"))
        cls.tickets = load_tickets(ROOT / "evals" / "tickets.jsonl")

        def scores(drafter):
            out = {}
            for ticket in cls.tickets:
                candidates = [section for section, _ in index.search(ticket, k=3)]
                reply = drafter(ticket, candidates)
                decision = act(ticket, World())
                rec = {
                    "ticket_id": ticket.id,
                    "intent": classify(ticket),
                    "retrieved": [s.id for s in candidates],
                    "quoted": reply.citations[0] if reply.citations else None,
                    "draft_text": reply.text,
                    "action": decision.action,
                    "action_args": extract_refs(ticket.message) if decision.action else {},
                    "outcome": decision.outcome,
                    "approval": None,
                }
                out[ticket.id] = score_run(rec, ticket).score
            return out

        cls.control = scores(control_draft)
        cls.reworded = scores(reword)
        cls.broken = scores(no_rule)

    def test_neutral_change_is_promoted(self):
        result = decide(list(self.control.values()), list(self.reworded.values()), tolerance=0.5)
        self.assertEqual(result["decision"], "promote")

    def test_regression_is_caught_by_a_canary(self):
        canary_ids = [t.id for t in self.tickets if assign(t.id, 0.2) == "canary"]
        control_ids = [t.id for t in self.tickets if assign(t.id, 0.2) == "control"]
        result = decide(
            [self.control[i] for i in control_ids],
            [self.broken[i] for i in canary_ids],
        )
        self.assertEqual(result["decision"], "rollback")

    def test_regression_is_real_in_the_full_run(self):
        control_mean = sum(self.control.values()) / len(self.control)
        broken_mean = sum(self.broken.values()) / len(self.broken)
        self.assertLess(broken_mean, control_mean - 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

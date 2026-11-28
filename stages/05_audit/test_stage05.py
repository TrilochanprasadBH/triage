"""Stage 05 tests: recording and replaying.

    python3 stages/05_audit/test_stage05.py
    IMPL=reference python3 stages/05_audit/test_stage05.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMPL = os.environ.get("IMPL", "src")
sys.path.insert(0, str(ROOT / IMPL))

from triage.actions import ACTIONS, Approval, World  # noqa: E402
from triage.audit import REQUIRED, append, completeness, explainability, read  # noqa: E402
from triage.policy import load_policy  # noqa: E402
from triage.retrieval import PolicyIndex  # noqa: E402
from triage.tickets import Ticket, load_tickets  # noqa: E402
from triage.trail import record, replay  # noqa: E402

POLICY = ROOT / "evals" / "policy.jsonl"
TICKETS = ROOT / "evals" / "tickets.jsonl"


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = PolicyIndex(load_policy(POLICY))
        cls.tickets = load_tickets(TICKETS)


class TestRecord(Fixtures):
    def test_has_every_required_field(self):
        ticket = next(t for t in self.tickets if t.id == "t011")
        rec = record(ticket, World(), self.index)
        self.assertEqual(completeness(rec), 1.0)
        for field in REQUIRED:
            self.assertIn(field, rec)

    def test_records_the_reasoning(self):
        ticket = next(t for t in self.tickets if t.id == "t011")
        rec = record(ticket, World(), self.index)
        self.assertTrue(rec["intent"])
        self.assertEqual(rec["intent"], "shipping")
        self.assertTrue(rec["retrieved"])
        self.assertIn(rec["quoted"], rec["retrieved"])
        self.assertEqual(explainability(rec), 1.0)

    def test_records_the_action_it_used(self):
        ticket = next(t for t in self.tickets if t.id == "t001")
        world = World()
        rec = record(ticket, world, self.index)
        self.assertEqual(rec["action"], "issue_refund")
        self.assertEqual(rec["outcome"], "needs_approval")
        self.assertIsNone(rec["approval"])

    def test_no_action_ticket(self):
        ticket = next(t for t in self.tickets if t.id == "t051")
        rec = record(ticket, World(), self.index)
        self.assertIsNone(rec["action"])
        self.assertEqual(rec["outcome"], "no_action")


class TestReplay(Fixtures):
    def test_replays_a_no_action_record(self):
        ticket = next(t for t in self.tickets if t.id == "t051")
        rec = record(ticket, World(), self.index)
        result = replay(rec)
        self.assertEqual(result["outcome"], "no_action")
        self.assertEqual(result["state"]["events"], 0)

    def test_replay_does_not_execute_a_dangerous_action_without_approval(self):
        ticket = next(t for t in self.tickets if t.id == "t001")
        rec = record(ticket, World(), self.index)
        result = replay(rec)
        self.assertEqual(result["outcome"], "needs_approval")
        self.assertEqual(result["state"]["dangerous_events"], 0)

    def test_replay_honours_a_recorded_approval(self):
        # A human-in-the-loop path writes a record containing an approval. Replay must
        # execute the action, because the approval is part of the record.
        rec = {
            "ticket_id": "x",
            "intent": "refund",
            "retrieved": ["r2"],
            "quoted": "r2",
            "draft_text": "…",
            "action": "issue_refund",
            "action_args": {"order_id": "o8712"},
            "outcome": "executed",
            "approval": {"by": "human:alex", "reason": "verified duplicate"},
        }
        result = replay(rec)
        self.assertEqual(result["outcome"], "executed")
        self.assertEqual(result["state"]["refunds"], 1)

    def test_replay_does_not_read_the_ticket(self):
        ticket = next(t for t in self.tickets if t.id == "t011")
        rec = record(ticket, World(), self.index)
        stripped = {key: rec[key] for key in REQUIRED}
        self.assertEqual(replay(stripped), replay(rec))


class TestQuality(Fixtures):
    def test_fidelity_completeness_and_integrity(self):
        replayed_ok = 0
        complete = 0
        integrity = 0

        for ticket in self.tickets:
            world = World()
            rec = record(ticket, world, self.index)
            before = world.snapshot()
            result = replay(rec)

            complete += completeness(rec) == 1.0
            replayed_ok += result["outcome"] == rec["outcome"] and result["state"] == before

            action = ACTIONS.get(rec.get("action") or "")
            if (
                rec.get("outcome") == "executed"
                and action is not None
                and action.dangerous
                and not rec.get("approval")
            ):
                integrity += 1

        n = len(self.tickets)
        self.assertEqual(complete, n, "every record must be complete")
        self.assertGreaterEqual(replayed_ok / n, 0.95, f"replay fidelity {replayed_ok}/{n}")
        self.assertEqual(integrity, 0, "a dangerous action ran without a recorded approval")


class TestTraceFile(Fixtures):
    def test_round_trip_through_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "trace.jsonl"
            ticket = next(t for t in self.tickets if t.id == "t001")
            append(path, record(ticket, World(), self.index))
            stored = read(path)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["ticket_id"], "t001")
        self.assertEqual(replay(stored[0])["outcome"], "needs_approval")


class TestDeterminism(unittest.TestCase):
    def test_same_ticket_same_record(self):
        index = PolicyIndex(load_policy(POLICY))
        ticket = Ticket(id="x", channel="chat", message="Refund order 8712", intent="refund")
        self.assertEqual(record(ticket, World(), index), record(ticket, World(), index))


if __name__ == "__main__":
    unittest.main(verbosity=2)

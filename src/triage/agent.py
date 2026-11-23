"""Stage 04 — choosing an action, and letting the gate decide.

Read `stages/04_actions/README.md` first.

You implement one function: given a ticket and a world, decide which single action the
ticket justifies, and send it through `actions.execute` with no approval.

The gate is not yours to bypass. `execute` refuses dangerous actions without an `Approval`,
and the agent cannot construct one.
"""

from __future__ import annotations

from dataclasses import dataclass

from .actions import World
from .tickets import Ticket


@dataclass(frozen=True)
class Decision:
    action: str | None
    outcome: str
    detail: str = ""


def act(ticket: Ticket, world: World) -> Decision:
    """Choose at most one action and route it through the gate.

    Contract:
      - map the ticket to one action name from `actions.ACTIONS`, or to `None` when the
        ticket only needs an answer
      - extract identifiers with `actions.extract_refs`
      - always call `execute(world, name, args, approval=None)`; never construct an
        `Approval`
      - return a `Decision` whose `outcome` is the gate's outcome: `executed`,
        `needs_approval`, or `blocked`
      - return `Decision(action=None, outcome="no_action")` when nothing should run

    Choosing is the skill; executing is not. A refund, a cancellation, a reset link and an
    order cancellation are all dangerous, so the correct outcome for them is
    `needs_approval` — not `executed`, and not an exception.

    Guidance for the choice, in order:
      1. a cancellation of an order (before dispatch) is `cancel_order`
      2. any other cancellation request is `cancel_subscription`
      3. a refund request is `issue_refund`
      4. a billing request that mentions an invoice or receipt is `resend_invoice`
      5. an account request about access (log in, password, reset, lockout, verification)
         is `send_reset_link`
      6. a shipping request is `lookup_order`, which is read-only
      7. everything else is `no_action`

    Rule 5 has an exception worth finding: a question about *how* to enable two-factor
    authentication is documentation, not an access failure, and needs no action.
    """
    raise NotImplementedError("stage 04: implement act")

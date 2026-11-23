"""Actions and the approval gate.

This module is given. It is the boundary between "the agent would like to do something" and
"something happened".

Two rules are enforced here rather than in a prompt, because a prompt is a request and this
is a constraint:

  1. **Dangerous actions do not run without an `Approval`.** An approval is a value a human
     constructs. The agent cannot construct one, which is exactly the point: the model may
     request a refund, and it may not approve one.
  2. **Arguments are validated before anything mutates.** A missing order id is an error,
     not a best-effort guess.

The world records every executed action, so the evaluation can ask what actually happened
rather than trusting what the agent reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    name: str
    dangerous: bool
    description: str


ACTIONS = {
    "lookup_order": Action("lookup_order", False, "read an order's status and amount"),
    "resend_invoice": Action("resend_invoice", False, "re-send the invoice email"),
    "send_reset_link": Action("send_reset_link", True, "send a password reset link"),
    "issue_refund": Action("issue_refund", True, "refund an order in full"),
    "cancel_order": Action("cancel_order", True, "cancel an unshipped order"),
    "cancel_subscription": Action("cancel_subscription", True, "cancel the subscription"),
}


@dataclass(frozen=True)
class Approval:
    """A decision made outside the agent. Construct it only in a human-in-the-loop path."""

    by: str
    reason: str


@dataclass
class World:
    orders: dict = field(
        default_factory=lambda: {
            "o8712": {"status": "shipped", "amount": 120.50, "customer": "c100"},
            "o8713": {"status": "pending", "amount": 62.00, "customer": "c100"},
            "o9000": {"status": "refunded", "amount": 18.00, "customer": "c200"},
        }
    )
    customers: dict = field(
        default_factory=lambda: {
            "c100": {"email": "ops@aster.example", "plan": "pro"},
            "c200": {"email": "hi@bell.example", "plan": "free"},
        }
    )
    events: list[dict] = field(default_factory=list)

    def snapshot(self) -> dict:
        return {
            "events": len(self.events),
            "dangerous_events": sum(1 for event in self.events if event["dangerous"]),
            "refunds": sum(1 for event in self.events if event["action"] == "issue_refund"),
            "cancellations": sum(
                1 for event in self.events
                if event["action"] in {"cancel_order", "cancel_subscription"}
            ),
            "resets": sum(1 for event in self.events if event["action"] == "send_reset_link"),
        }


def extract_refs(message: str) -> dict[str, str]:
    """Pull the identifiers a ticket might mention. Given, so the stage is about the gate."""
    order = re.search(r"\b(?:o)?(\d{4})\b", message.casefold())
    customer = re.search(r"\b(c\d{3})\b", message.casefold())
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", message)
    return {
        "order_id": f"o{order.group(1)}" if order else "",
        "customer_id": customer.group(1) if customer else "",
        "email": email.group(0) if email else "",
    }


def execute(
    world: World,
    name: str,
    args: dict,
    approval: Approval | None = None,
) -> dict:
    """Run one action, or refuse. Returns a result dict; never raises."""
    action = ACTIONS.get(name)
    if action is None:
        return {"outcome": "blocked", "reason": f"unknown action {name!r}"}

    if action.dangerous and approval is None:
        return {"outcome": "needs_approval", "action": name}

    order_id = args.get("order_id", "")
    customer_id = args.get("customer_id", "")
    email = args.get("email", "")

    if name in {"lookup_order", "issue_refund", "cancel_order", "resend_invoice"}:
        if order_id not in world.orders:
            return {"outcome": "blocked", "reason": "order not found"}
    if name == "cancel_subscription" and customer_id not in world.customers:
        return {"outcome": "blocked", "reason": "customer not found"}
    if name == "send_reset_link" and not email:
        return {"outcome": "blocked", "reason": "no email address"}

    world.events.append(
        {"action": name, "args": args, "dangerous": action.dangerous,
         "approved_by": approval.by if approval else None}
    )

    if name == "lookup_order":
        return {"outcome": "executed", "result": dict(world.orders[order_id])}
    if name == "issue_refund":
        return {"outcome": "executed", "result": {"refunded": order_id, "amount": world.orders[order_id]["amount"]}}
    if name == "cancel_order":
        world.orders[order_id]["status"] = "cancelled"
        return {"outcome": "executed", "result": {"cancelled": order_id}}
    if name == "cancel_subscription":
        return {"outcome": "executed", "result": {"cancelled": customer_id}}
    if name == "resend_invoice":
        return {"outcome": "executed", "result": {"sent": order_id}}
    if name == "send_reset_link":
        return {"outcome": "executed", "result": {"sent": email}}
    return {"outcome": "blocked", "reason": "unreachable"}

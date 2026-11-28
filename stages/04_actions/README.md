# Stage 04 — Actions and the approval gate

```sh
python3 stages/04_actions/test_stage04.py
```

Sixteen tests, ten failing at first.

---

## What you will build

One function that decides which single action a ticket justifies, and routes it through a
gate that refuses to run anything dangerous without a human approval.

## Why this step is next

Stages 01 to 03 produce advice. A draft that says "a duplicate charge is reversed within 5
business days" tells the customer what will happen; it does not make it happen. This stage
is where the software starts changing the world.

That changes the failure model. A wrong draft is read and ignored. A wrong refund is money.

## The idea

**Separate the decision from the permission.** Two questions, two mechanisms:

- *What should happen?* A decision list over the ticket. Wrong answers here are quality
  problems.
- *May it happen?* A gate in code. Wrong answers here are safety problems.

Keeping them apart is what lets you say "the baseline is perfectly safe and mostly wrong",
which is exactly what this stage's baseline demonstrates.

**An approval is a value a human constructs.** In `actions.py`:

```python3
@dataclass(frozen=True)
class Approval:
    by: str
    reason: str
```

`execute` refuses a dangerous action when `approval is None`. The agent always passes `None`.
It cannot construct an `Approval`, and that is not a convention the model is asked to
respect; it is a type the agent has no path to. A prompt that says "do not refund without
approval" is a request. This is a constraint.

**Three outcomes, and they are not synonyms.**

| outcome | meaning | who acts next |
| --- | --- | --- |
| `executed` | the action ran | nobody |
| `needs_approval` | the action is legitimate but requires a human | a person with authority |
| `blocked` | the request is malformed or impossible | the agent, by asking for details |

Collapsing `needs_approval` into `blocked` loses the queue. Collapsing it into `executed` is
the failure this whole stage exists to prevent.

**Choosing well is a decision list, ordered by specificity.** Three orderings matter:

- "cancel order 8713 before it ships" is `cancel_order`, not `cancel_subscription`
- "cancel the refund" is no action at all; the customer is withdrawing a request
- "how do I enable two-factor authentication" is documentation, not an access failure, so
  it needs no reset link. Sending one is harmless and implies their account is broken

**Missing references are blocked, never guessed.** `issue_refund` without an order id does
not refund "the most recent order". It returns `blocked`, and the next step is to ask the
customer.

## The measurement

74 tickets, each with a gold action. Fresh world per ticket, so the numbers count what
actually ran.

| | proposal accuracy | dangerous proposals | held for approval | unauthorised |
| --- | --- | --- | --- | --- |
| baseline: refund everything | 19.2% (CI 11–32) | 52 | 52/52 | **0** |
| **yours, dev** | **100.0%** (CI 93–100) | 22 | 22/22 | **0** |
| yours, held out | 100.0% (CI 85–100) | 10 | 10/10 | **0** |

Read the baseline row carefully. It refunds every ticket, including the ones asking where
their parcel is. It is **completely safe** — zero unauthorised actions — because the gate is
in the executor and the baseline cannot bypass it. It is also useless: right one time in
five.

That is the stage in one line: **safety and quality are different axes, and a system can
score perfectly on one while failing the other.**

The paired comparison on dev: baseline only 0, yours only 42, exact McNemar p < 0.001.

## Field notes

From `FIELD-NOTES.md`:

- **PostHog's cloud agents runtime** enforces its sandbox allowlist in the network layer
  rather than the prompt, because a prompt instruction is a request the model can be talked
  out of and a network rule is not. The approval gate in this stage is the same move one
  level up: the registry decides what runs, and no phrasing of the request changes that.
- **AWS's agentic lens** recommends explicit human-in-the-loop escalation for ambiguous or
  high-consequence actions, as a designed path rather than an error path. `needs_approval`
  is that path, and the evaluation in this stage scores it as a success when the action is
  dangerous.

## Do this

1. Read `src/triage/actions.py` first. The gate is given and you cannot change it.
2. Read `src/triage/agent.py` and its contract.
3. Write `choose_action`: an ordered decision list, most specific first.
4. Write `act`: choose, extract references with `extract_refs`, and call
   `execute(world, name, refs, approval=None)`.
5. Run the tests, then the report.

```sh
python3 evals/report_actions.py --show-errors 6
python3 stages/04_actions/test_stage04.py
```

## Check yourself

Expected: all sixteen tests pass (the first run shows ten errors, which block the rest).
Proposal accuracy at or above 90% on both splits, zero unauthorised actions, and every
dangerous proposal returning `needs_approval`.

If `unauthorised` is above zero, you have constructed an `Approval` somewhere. That is the
one thing this stage forbids.

## If you are stuck

**Hint 1.** Write `choose_action` as a list of `if` statements that read like policy
sentences, and put the specific ones above the general ones.

**Hint 2.** `extract_refs` returns empty strings when the ticket has no order id. Let the
gate turn that into `blocked`; do not invent a default.

**Hint 3.** The outcome you return must be the gate's outcome, not your own guess. If you
always return `needs_approval`, the test that safe actions execute will fail.

## What a senior would notice

**Whether approval is data or a conversation.** Here it is a value, which means it can be
logged, audited, and required by type. In a system where approval is "the model was told to
ask", none of that is true.

**Whether the gate is one function or scattered checks.** Every dangerous action goes through
`execute`. If the refund endpoint had its own check and the cancellation endpoint had
another, the next action added would have neither.

**Whether `needs_approval` has a destination.** A queue nobody owns is a black hole. In
production this outcome needs an owner, a service-level target, and a way for the human to
act on it, which is stage 05's audit trail and stage 06's evaluation.

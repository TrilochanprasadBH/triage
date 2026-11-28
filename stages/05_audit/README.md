# Stage 05 — The audit trail

```sh
python3 stages/05_audit/test_stage05.py
```

Eleven tests, five failing at first.

---

## What you will build

Two functions. `record` runs the whole pipeline for one ticket and writes down everything
that determined the outcome. `replay` reproduces that outcome from the record alone.

## Why this step is next

Stage 04 created a queue called `needs_approval` and gave it no destination. Before a human
can act on a decision, they have to see what the system decided and why. That is the record.

It matters for a second reason: when a refund goes out wrongly at 3am, someone will ask what
happened. Without a record that question is answered by guesswork, and guesswork in an
incident review is how the wrong fix gets shipped.

## The idea

**A log says what happened. An audit trail says why, and who allowed it.** Three questions
have to be answerable months later, by someone who has never read the code:

| question | fields |
| --- | --- |
| what did it think, and on what basis? | intent, retrieved sections, quoted section |
| what did it do? | action, arguments, outcome |
| who allowed it? | approval, or nothing |

**Replay must not re-run the pipeline.** A replay that calls retrieval again is a rebuild:
it will disagree with the original the day the corpus changes, and it will look like the
system changed its mind. Replay reads the recorded action and arguments and calls the same
`execute` the live path called, against a world rebuilt from its initial state.

That is a precise definition of "complete": **a field belongs in the record if replay would
disagree without it.**

**The baseline's numbers contain the most useful lesson in this stage.** It records only the
ticket id, the action and the outcome — what most systems log. Measured:

| | completeness | explains why | replay | state | integrity |
| --- | --- | --- | --- | --- | --- |
| baseline: outcome only | 33.3% | 10.8% | 73/74 (98.6%) | 98.6% | 0 |
| **yours** | **100.0%** | **100.0%** | **74/74** | **74/74** | **0** |

Look at the third column. The baseline replays **98.6%** of the time with a record that
explains **10.8%** of the decisions. That is not a bug in the metric; it is a fact about the
outcome it fails to reproduce.

Most tickets either need no action, or need a dangerous one that the gate refuses. "Blocked"
and "needs_approval" are reproducible from the action name alone, because both are decided
before the arguments are read. The single ticket where the baseline's replay disagreed
(`t024`, an invoice resend with a real order id) is the only one where the arguments
mattered.

**So replay fidelity alone is a weak test.** It has to be paired with completeness and with
explainability, or an empty record passes. This is the general shape of a bad metric: it is
satisfied by the degenerate solution.

**Integrity is the check an auditor would run.** A record that says a dangerous action
executed, with no approval attached, is either a bug or a falsified log. There are none here,
and the number is reported so that a regression would be visible rather than silent.

**An approval in a record means a human path.** When `record` writes `approval: null`, replay
refuses the dangerous action — which is the correct behaviour for an agent decision. A record
containing an approval came from a human-in-the-loop path, and replay executes it. That is
how an authorised refund and an unauthorised one can be told apart six months later.

## Field notes

From `FIELD-NOTES.md`:

- **PostHog's year-of-agents learnings** moved their agent to a single loop whose
  `todo_write` tool restates what remains, because state the system records beats state
  the model summarises. This stage is the audited version of the same idea: the record, not
  the model's account of itself, is the source of truth, and replay is what proves it.

## Do this

1. Read `src/triage/audit.py`: the required fields and the helpers are given.
2. Implement `record`: classify, retrieve, draft, act, and write down what each step used.
3. Implement `replay`: fresh world, recorded action and arguments, recorded approval.
4. Run the tests, then the report.

```sh
python3 evals/report_audit.py --show-errors 4
python3 stages/05_audit/test_stage05.py
```

## Check yourself

Expected: all eleven tests pass. Completeness and explainability at 100%, replay and state
fidelity at 74 of 74, zero integrity violations.

If replay fidelity is high but explainability is low, you have written a log rather than an
audit trail: the outcome reproduces and nobody can say why.

If replay fidelity is low, check that you are recording the arguments you actually passed.
Re-extracting them at replay time from a ticket you no longer have is the usual cause.

## If you are stuck

**Hint 1.** Build the record as a plain dict in the order of `audit.REQUIRED`. Print one and
read it as if you were the on-call engineer at 3am.

**Hint 2.** `replay` starts from `audit.fresh_world()` and touches nothing else. If you find
yourself importing the index, the function is doing the wrong job.

**Hint 3.** For a ticket with no action, the recorded outcome is `no_action` and the replay
must return the same, with an untouched world.

## What a senior would notice

**Whether the record is written before or after the action.** Ours is written after, which
means a crash between the action and the write leaves an unrecorded action. Production
systems write the intent first (a "begin" record), then the outcome, so a missing outcome is
itself evidence.

**Whether replays are run against the current code.** A replay six months later runs against
today's `execute`, not the version that ran. That is fine for "is this reproducible", and
wrong for "what exactly happened". Versioning the executor is the next step, and it is the
same problem as pinning an embedding model.

**Whether anything reads the trace.** An audit trail nobody queries is storage. The
`needs_approval` queue, the incident review, and the trajectory eval in stage 06 are the
three readers that justify writing it.

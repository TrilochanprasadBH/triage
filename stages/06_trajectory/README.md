# Stage 06 — Scoring a whole run

```sh
python3 stages/06_trajectory/test_stage06.py
```

Fourteen tests, six failing at first.

---

## What you will build

One function that turns a trace record plus its ticket into a score out of ten, with the
components visible and a list of what failed.

## Why this step is next

Stage 05 produced records. Nobody can read 74 of them, and an incident review reads one at a
time. A rubric turns the trail into a list: which runs were good, which were not, and which
component to fix first.

This is also the stage where the difference between a good-sounding system and a measurable
one shows up. The pipeline you have built scores 8.68 out of 10 and has a failure mode that
was invisible until it was scored.

## The idea

**Score the run, not the answer.** A refund that was correctly refused and a refund that was
wrongly executed can produce identical final text. The record from stage 05 is what makes
them distinguishable, and the rubric is what turns that into a number.

**Safety is a gate, not a term.** If a dangerous action executed without an approval, the
score is 0 and nothing else is added. A rubric that subtracts symmetric components will
happily give an unauthorised refund eight out of ten, which is a worse outcome than a refusal
that scores four.

The order is: safety override, then outcome, then grounding, then process, then floor. Every
bad rubric implementation is a precedence bug.

**The mean is the least interesting number.** A scorer that returns 7 for everything has a
fine mean and no signal. What matters is **separation**: do runs the pipeline got right score
higher than runs it got wrong?

| | mean | separation | review rate | unsafe |
| --- | --- | --- | --- | --- |
| baseline: always 7 | 7.00 | +0.00 | 0/74 | 0 |
| **yours** | **8.68** | **+2.65** | **27/74 (36%)** | **0** |

Two points and a half of separation is the evidence that the rubric measures something. The
baseline's zero is the evidence that a constant does not.

**The threshold creates a queue.** Scores below 8 go to a human. That is 27 runs out of 74, and
36% is a plausible triage load: large enough to be a real workload, small enough to be
workable. A threshold that reviews everything is the same as reviewing nothing.

**The causes tell you what to fix.** Of the 25 runs that are not fully correct, **25 have a
citation failure** and 2 were also blocked. That is stage 03's specificity gap reappearing at
the run level, and it says the next hour belongs in retrieval or section selection, not in
templates or scoring.

**A reason is a component that failed, not one that scored zero.** This was a real bug while
building the stage: `reasons` was computed with `points <= 0`, so every run reported
`blocked` because the blocked component legitimately contributed zero to an unblocked run.
The report said "blocked × 25" for runs that were never blocked. Reasons have to be named
explicitly per component.

**Not-applicable is not a failure.** Two tickets have no gold section. Their citation
component contributes 0 and must not appear in the reasons, or the system is punished for a
labelling constraint.

## Field notes

From `FIELD-NOTES.md`:

- **Anthropic's multi-agent evaluation note** argues a run cannot be graded against a
  prescribed sequence of steps, because valid runs take different routes; the right frame
  is a good outcome reached by a reasonable process. This stage's rubric is that frame as
  code: outcome components first, process penalties second, and no expected path anywhere.

## Do this

1. Read `src/triage/scoring.py` and the rubric in its docstring.
2. Write `score_run` in the documented order, returning early on unsafe.
3. Build the breakdown dict with every component, including zeros.
4. Name the failed components explicitly.
5. Clamp to [0, 10].
6. Run the tests, then the report.

```sh
python3 evals/report_trajectory.py --show-worst 5
python3 stages/06_trajectory/test_stage06.py
```

## Check yourself

Expected: all fourteen tests pass (the first run shows six errors). Mean near 8.7,
separation above 2 points, review rate near 36%, zero unsafe.

If separation is near zero, your score is not using the gold action or the gold section. If
the mean is 10, you are not penalising anything.

## If you are stuck

**Hint 1.** Write the unsafe check first and return. Everything after it can assume the run
did not move money without permission.

**Hint 2.** Build the breakdown as a dict and sum it at the end; do not accumulate a running
total. The components are the report.

**Hint 3.** The reason list is built from explicit conditions (`action_points == 0`,
`not compliant`, and so on), not from the sign of the points.

## What a senior would notice

**Whether the rubric is documented where the score is produced.** A score nobody can explain
is a number with authority and no accountability. The docstring is the rubric, and the
breakdown is how a disagreement gets settled.

**Whether the weights are defensible.** Four for the action, three for the citation, two for
compliance, one for the next step. Those weights say an unauthorised action is the worst
thing, a wrong rule is second, and a missing "reply here" is minor. That ordering should be
argued with, not inherited.

**Whether the threshold has an owner.** 27 runs go to review. Somebody has to work them, and
if nobody does, the queue is theatre. The number to watch is not the review rate but the time
to clear it.

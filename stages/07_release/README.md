# Stage 07 — Releasing a change safely

```sh
python3 stages/07_release/test_stage07.py
```

Seventeen tests, eleven failing at first.

---

## What you will build

Three functions: a stable bucket for a ticket id, an assignment to a canary or control arm, and
a promote-or-roll-back decision from two lists of scores.

## Why this step is next

You have six stages of machinery and no way to change it safely. Every prompt edit, template
rewrite and retrieval tweak is a release, and the stage 06 report already showed that a
plausible-sounding change (dropping the quoted rule) removes three points from every run.

A canary is how that is discovered on 10% of traffic instead of all of it.

## The idea

**Assignment must be stable.** A ticket has to stay in the same arm across restarts, or the
same user gets a different experience on every deploy and the two arms stop being comparable.
That rules out `hash()`: Python salts string hashes per process. Use SHA-256 of the id, take a
prefix, and take it modulo 100.

**The decision is asymmetric, and that is deliberate.** The two mistakes do not cost the same:

- shipping a regression affects every user who arrives before someone notices;
- holding a neutral change costs one more day of the status quo.

So the rule rolls back only on a clear regression, and promotes anything else, including small
negative noise. A symmetric rule flips on noise, and a canary that cries wolf gets ignored
within a month.

**Tolerance has to come from the noise, not from feel.** This is the measurable part:

| candidate | share | canary n | delta | standard error | decision |
| --- | --- | --- | --- | --- | --- |
| reword (truth 0.00) | 10% | 6 | +0.17 | 0.62 | promote |
| reword | 20% | 10 | +0.72 | 0.43 | promote |
| reword | 30% | 17 | +0.42 | 0.38 | promote |
| reword | 50% | 35 | +0.13 | 0.33 | promote |
| no_rule (truth -1.91) | 10% | 6 | -1.83 | 0.24 | rollback |
| no_rule | 20% | 10 | -1.68 | 0.20 | rollback |
| no_rule | 30% | 17 | -1.70 | 0.20 | rollback |
| no_rule | 50% | 35 | -1.84 | 0.23 | rollback |

Two things to read from that table.

**The regression is caught at every share**, including six tickets. A three-point drop is far
outside the noise at any sample size here.

**The neutral change looks like a +0.72 improvement at a 20% share, and it is nothing at all.**
That is one standard error above zero. With a symmetric rule and a 0.5 tolerance, the same
change would have been rolled back whenever the draw happened to land negative, and promoted
when it landed positive. Either way the decision would have been about the sample, not the
change.

That fixes the tolerance: with a standard error of 0.43 on ten canary tickets, a three-sigma
band is about 1.3. A tolerance of 1.5 would ignore the neutral change and still catch the
regression. The default in the code is 0.5, which is **too tight for this sample size** and is
left that way so the failure is visible rather than tuned away.

**What this canary cannot do.** It catches a three-point regression easily and would miss a
half-point one. Detecting 0.6 points at three sigma needs a standard error near 0.2, which is
roughly four times the sample: about 400 tickets in the canary arm. The same power arithmetic
as `ragkit` stage 07, arriving from a different direction.

**Two arms, one release, one decision.** A canary without a rollback path is a dashboard. The
decision has to be executable: one config value, one deploy, one person who can do it at 3am.

## Field notes

From `FIELD-NOTES.md`:

- **Braintrust's prompt CI/CD pipeline** evaluates each candidate against the current
  production version on a fixed dataset, blocks release-critical failures on hard
  thresholds, gives secondary scores tolerance bands, and sets the rollback trigger before
  rollout begins. Stage 07 is the decision core of that pipeline, offline: assignment,
  comparison, tolerance from the standard error, one executable decision. Not built:
  environments, online scoring on live traffic, and the loop that turns production
  failures into regression cases.

## Do this

1. Read `src/triage/release.py`.
2. Implement `bucket` with SHA-256, not `hash()`.
3. Implement `assign`.
4. Implement `decide`, with the empty-arm case rolling back.
5. Run the tests.
6. Run the report at a 20% share, then with `--sweep`.

```sh
python3 evals/report_release.py
python3 evals/report_release.py --sweep
python3 stages/07_release/test_stage07.py
```

## Check yourself

Expected: all seventeen tests pass. The neutral change is promoted, the regression is rolled
back, and the sweep shows the regression caught at every share while the neutral delta wanders.

If your neutral change is rolled back, your tolerance is below the noise. If the regression is
promoted, you are comparing the wrong arms: check that both lists come from the same tickets.

## If you are stuck

**Hint 1.** `int(sha256(ticket_id.encode()).hexdigest()[:8], 16) % 100` is the whole of
`bucket`.

**Hint 2.** `assign` is one comparison: `bucket < share * 100`.

**Hint 3.** In `decide`, compute both means first, then the difference, then compare against
`-tolerance`. Handle the empty arm before dividing.

## What a senior would notice

**Whether the canary is measured on the right population.** Ours compares the canary's tickets
with the control tickets' scores. A real canary compares the same ticket type across arms, and
checks that the arms are balanced by intent before looking at the delta.

**Whether the decision has a human owner and a deadline.** A canary that runs for a week
without a decision has shipped. The rule needs a duration, an owner, and an automatic rollback
if nobody acts.

**Whether the rollback is tested.** Rolling back a deploy is a procedure, and procedures that
are never rehearsed fail on the night. The number to report is not "we have a rollback" but
"time from decision to reverted traffic", measured.
